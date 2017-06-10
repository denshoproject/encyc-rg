# -*- coding: utf-8 -*-

from collections import OrderedDict
import json
import logging
logger = logging.getLogger(__name__)

from elasticsearch_dsl import Index, Search, A
from elasticsearch_dsl.connections import connections

from django.conf import settings

from .models import DOCTYPE_CLASS, SEARCH_LIST_FIELDS, PAGE_BROWSABLE_FIELDS
from .models import NotFoundError


# set default hosts and index
connections.create_connection(hosts=settings.DOCSTORE_HOSTS)
INDEX = Index(settings.DOCSTORE_INDEX)


class SearchResults(object):
    """Nicely packaged search results for use in API and UI.
    
    >>> from rg import search
    >>> q = {"fulltext":"minidoka"}
    >>> sr = search.run_search(request_data=q, request=None)
    """
    query = {}
    _request = None
    aggregations = None
    objects = []
    total = -1
    limit = -1
    offset = -1
    page_size = -1
    prev_page_api = ''
    next_page_api = ''
    this_page = -1
    prev_page = ''
    next_page = ''

    def __init__(self, query={}, results=None, objects=[], limit=settings.DEFAULT_LIMIT, offset=0, request=None):
        if not (results or objects):
            raise Exception('SearchResults requires an ES result set or a list of objects.')
        self.query = query
        self._request = request
        self.limit = int(limit)
        self.offset = int(offset)
        self.page_size = self.limit
        
        if results:
            self.objects = [
                DOCTYPE_CLASS[hit['_type']].dict_list(hit, self._request)
                for hit in results.hits.hits
            ]
            self.aggregations = getattr(results, 'aggregations', {})
            self.total = int(results.hits.total)

        elif objects:
            self.objects = objects
            self.total = len(self.objects)
        
        # API pagination
        p = offset - limit
        n = offset + limit
        if p < 0:
            p = None
        if n >= self.total:
            n = None
        if p is not None:
            self.prev_page_api = '?limit=%s&offset=%s' % (limit, p)
        if n:
            self.next_page_api = '?limit=%s&offset=%s' % (limit, n)
        
        # Django pagination
    
    def ordered_dict(self):
        """Express search results in API and Redis-friendly dict
        
        returns: OrderedDict
        """
        data = OrderedDict()
        data['total'] = self.total
        data['page_size'] = self.limit
        data['prev_page'] = self.prev_page_api
        data['next_page'] = self.next_page_api
        data['objects'] = []
        for o in self.objects:
            if isinstance(o, dict) or isinstance(o, OrderedDict):
                data['objects'].append(o)
            else:
                data['objects'].append(
                    o.to_dict_list(request=self._request)
                )
        data['query'] = self.query
        return data


def run_search(request_data, request, sort_fields=[], limit=settings.DEFAULT_LIMIT, offset=0):
    """Return object children list in Django REST Framework format.
    
    Returns a paged list with count/prev/next metadata
    
    @returns: dict
    """
    q = OrderedDict()
    q = {}
    q['fulltext'] = request_data.get('fulltext')
    q['must'] = request_data.get('must', [])
    q['should'] = request_data.get('should', [])
    q['mustnot'] = request_data.get('mustnot', [])
    q['doctypes'] = request_data.get('doctypes', [])
    q['sort'] = request_data.get('sort', [])
    q['offset'] = request_data.get('offset', 0)
    q['limit'] = request_data.get('limit', limit)
    
    if not (q['fulltext'] or q['must'] or q['should'] or q['mustnot']):
        return q,[]

    if not isinstance(q['doctypes'], basestring):
        doctypes = q['doctypes']
    elif isinstance(q['doctypes'], list):
        doctypes = ','.join(q['doctypes'])
    else:
        raise Exception('doctypes must be a string or a list')
    if not doctypes:
        doctypes = DOCTYPE_CLASS.keys()
    
    query = prep_query(
        text=q['fulltext'],
        must=q['must'],
        should=q['should'],
        mustnot=q['mustnot'],
        aggs={},
    )
    logger.debug(json.dumps(query))
    if not query:
        raise Exception("Can't do an empty search. Give me something to work with here.")
    
    sort_cleaned = _clean_sort(q['sort'])
    
    s = Search.from_dict(query)
    for d in doctypes:
        s = s.doc_type(DOCTYPE_CLASS[d])
    #s = s.sort(...)
    #s = s[from_:from_ + size]
    s = s.source(
        include=SEARCH_LIST_FIELDS,
        exclude=[],
    )
    results = s.execute()
    return SearchResults(
        query=query,
        results=results,
        limit=limit,
        offset=offset,
        request=request,
    )

def prep_query(text='', must=[], should=[], mustnot=[], aggs={}):
    """Assembles a dict conforming to the Elasticsearch query DSL.
    
    Elasticsearch query dicts
    See https://www.elastic.co/guide/en/elasticsearch/guide/current/_most_important_queries.html
    - {"match": {"fieldname": "value"}}
    - {"multi_match": {
        "query": "full text search",
        "fields": ["fieldname1", "fieldname2"]
      }}
    - {"terms": {"fieldname": ["value1","value2"]}},
    - {"range": {"fieldname.subfield": {"gt":20, "lte":31}}},
    - {"exists": {"fieldname": "title"}}
    - {"missing": {"fieldname": "title"}}
    
    Elasticsearch aggregations
    See https://www.elastic.co/guide/en/elasticsearch/guide/current/aggregations.html
    aggs = {
        'formats': {'terms': {'field': 'format'}},
        'topics': {'terms': {'field': 'topics'}},
    }
    
    >>> from DDR import docstore,format_json
    >>> t = 'posthuman'
    >>> a = [{'terms':{'language':['eng','chi']}}, {'terms':{'creators.role':['distraction']}}]
    >>> q = docstore.search_query(text=t, must=a)
    >>> print(format_json(q))
    >>> d = ['entity','segment']
    >>> f = ['id','title']
    >>> results = docstore.Docstore().search(doctypes=d, query=q, fields=f)
    >>> for x in results['hits']['hits']:
    ...     print x['_source']
    
    @param text: str Free-text search.
    @param must: list of Elasticsearch query dicts (see above)
    @param should:  list of Elasticsearch query dicts (see above)
    @param mustnot: list of Elasticsearch query dicts (see above)
    @param aggs: dict Elasticsearch aggregations subquery (see above)
    @returns: dict
    """
    body = {
        "query": {
            "bool": {
                "must": must,
                "should": should,
                "must_not": mustnot,
            }
        }
    }
    if text:
        body['query']['bool']['must'].append(
            {
                "match": {
                    "_all": text
                }
            }
        )
    if aggs:
        body['aggregations'] = aggs
    return body

def _clean_dict(data):
    """Remove null or empty fields; ElasticSearch chokes on them.
    
    >>> d = {'a': 'abc', 'b': 'bcd', 'x':'' }
    >>> _clean_dict(d)
    >>> d
    {'a': 'abc', 'b': 'bcd'}
    
    @param data: Standard DDR list-of-dicts data structure.
    """
    if data and isinstance(data, dict):
        for key in data.keys():
            if not data[key]:
                del(data[key])

def _clean_sort( sort ):
    """Take list of [a,b] lists, return comma-separated list of a:b pairs
    
    >>> _clean_sort( 'whatever' )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc'], 'whatever'] )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc']] )
    'a:asc,b:asc'
    """
    cleaned = ''
    if sort and isinstance(sort,list):
        all_lists = [1 if isinstance(x, list) else 0 for x in sort]
        if not 0 in all_lists:
            cleaned = ','.join([':'.join(x) for x in sort])
    return cleaned

def execute(doctypes=[], query={}, sort=[], fields=[], from_=0, size=settings.MAX_SIZE):
    """Executes a query, get a list of zero or more hits.
    
    The "query" arg must be a dict that conforms to the Elasticsearch query DSL.
    See docstore.search_query for more info.
    
    @param doctypes: list Type of object ('collection', 'entity', 'file')
    @param query: dict The search definition using Elasticsearch Query DSL
    @param sort: list of (fieldname,direction) tuples
    @param fields: str
    @param from_: int Index of document from which to start results
    @param size: int Number of results to return
    @returns raw ElasticSearch query output
    """
    logger.debug('search(index=%s, doctypes=%s, query=%s, sort=%s, fields=%s, from_=%s, size=%s' % (
        INDEX, doctypes, query, sort, fields, from_, size
    ))
