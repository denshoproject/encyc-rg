from collections import OrderedDict
from copy import deepcopy
import json
import logging
logger = logging.getLogger(__name__)
import os
import re
from urllib.parse import quote, urlunsplit

from elasticsearch_dsl import Search
from elasticsearch_dsl.query import QueryString

from django.conf import settings

from . import docstore

#SEARCH_LIST_FIELDS = models.all_list_fields()

# whitelist of params recognized in URL query
# TODO derive from ddr-defs/repo_models/
# TODO THESE ARE FROM DDR!
SEARCH_PARAM_WHITELIST = [
    'published_encyc',
    'published_rg',
    'fulltext',
    'sort',
    'topics',
    'facility',
    'model',
    'models',
    'parent',
    'status',
    'public',
    'topics',
    'facility',
    'contributor',
    'creators',
    'format',
    'genre',
    'geography',
    'language',
    'location',
    'mimetype',
    'persons',
    'rights',
    'facet_id',
]

# fields where the relevant value is nested e.g. topics.id
# TODO derive from ddr-defs/repo_models/
SEARCH_NESTED_FIELDS = [
    'facility',
    'topics',
]

# TODO derive from ddr-defs/repo_models/
SEARCH_AGG_FIELDS = {
    'media-type': 'rg_rgmediatype',
}

# TODO derive from ddr-defs/repo_models/
SEARCH_MODELS = [
    'encycarticle',
]

# fields searched by query
# TODO derive from ddr-defs/repo_models/
SEARCH_INCLUDE_FIELDS = [
    'id',
    'model',
    'links_html',
    'links_json',
    'links_img',
    'links_thumb',
    'links_children',
    'status',
    'public',
    'title',
    'description',
    'contributor',
    'creators',
    'facility',
    'format',
    'genre',
    'geography',
    'label',
    'language',
    'location',
    'persons',
    'rights',
    'topics',
]


def es_offset(pagesize, thispage):
    """Convert Django pagination to Elasticsearch limit/offset
    
    >>> es_offset(pagesize=10, thispage=1)
    0
    >>> es_offset(pagesize=10, thispage=2)
    10
    >>> es_offset(pagesize=10, thispage=3)
    20
    
    @param pagesize: int Number of items per page
    @param thispage: int The current page (1-indexed)
    @returns: int offset
    """
    page = thispage - 1
    if page < 0:
        page = 0
    return pagesize * page

def start_stop(limit, offset):
    """Convert Elasticsearch limit/offset to Python slicing start,stop
    
    >>> start_stop(10, 0)
    0,9
    >>> start_stop(10, 1)
    10,19
    >>> start_stop(10, 2)
    20,29
    """
    start = int(offset)
    stop = (start + int(limit))
    return start,stop

def limit_offset(request):
    """Get limit,offset values from request
    
    @param request
    @returns: limit,offset
    """
    if request.GET.get('offset'):
        # limit and offset args take precedence over page
        limit = request.GET.get(
            'limit', int(request.GET.get('limit', settings.RESULTS_PER_PAGE))
        )
        offset = request.GET.get('offset', int(request.GET.get('offset', 0)))
    elif request.GET.get('page'):
        limit = settings.RESULTS_PER_PAGE
        thispage = int(request.GET['page'])
        offset = es_offset(limit, thispage)
    else:
        limit = settings.RESULTS_PER_PAGE
        offset = 0
    return limit,offset
    
def django_page(limit, offset):
    """Convert Elasticsearch limit/offset pagination to Django page
    
    >>> django_page(limit=10, offset=0)
    1
    >>> django_page(limit=10, offset=10)
    2
    >>> django_page(limit=10, offset=20)
    3
    
    @param limit: int Number of items per page
    @param offset: int Start of current page
    @returns: int page
    """
    return divmod(offset, limit)[0] + 1

def es_host_name(conn):
    """Extracts host:port from Elasticsearch conn object.
    
    >>> es_host_name(Elasticsearch(settings.DOCSTORE_HOST))
    "<Elasticsearch([{'host': '192.168.56.1', 'port': '9200'}])>"
    
    @param conn: elasticsearch.Elasticsearch with hosts/port
    @returns: str e.g. "192.168.56.1:9200"
    """
    start = conn.__repr__().index('[') + 1
    end = conn.__repr__().index(']')
    text = conn.__repr__()[start:end].replace("'", '"')
    hostdata = json.loads(text)
    return ':'.join([hostdata['host'], str(hostdata['port'])])


class SearchResults(object):
    """Nicely packaged search results for use in API and UI.
    
    >>> from rg import search
    >>> q = {"fulltext":"minidoka"}
    >>> sr = search.run_search(request_data=q, request=None)
    """

    def __init__(self, params={}, query={}, count=0, results=None, objects=[], limit=settings.PAGE_SIZE, offset=0):
        self.params = deepcopy(params)
        self.query = query
        self.aggregations = None
        self.objects = []
        self.total = 0
        try:
            self.limit = int(limit)
        except:
            self.limit = settings.MAX_SIZE
        try:
            self.offset = int(offset)
        except:
            self.offset = 0
        self.start = 0
        self.stop = 0
        self.prev_offset = 0
        self.next_offset = 0
        self.prev_api = u''
        self.next_api = u''
        self.page_size = 0
        self.this_page = 0
        self.prev_page = 0
        self.next_page = 0
        self.prev_html = u''
        self.next_html = u''
        self.errors = []
        
        if results:
            # objects
            self.objects = [hit for hit in results]
            if results.hits.total:
                self.total = results.hits.total.value

            # aggregations
            self.aggregations = {}
            if hasattr(results, 'aggregations'):
                for field in results.aggregations.to_dict().keys():
                    
                    # nested aggregations
                    if field in ['topics', 'facility']:
                        field_ids = '{}_ids'.format(field)
                        aggs = results.aggregations[field]
                        self.aggregations[field] = aggs[field_ids].buckets
                     
                    # simple aggregations
                    else:
                        aggs = results.aggregations[field]
                        self.aggregations[field] = aggs.buckets

        elif objects:
            # objects
            self.objects = objects
            self.total = len(objects)

        else:
            self.total = count

        # elasticsearch
        self.prev_offset = self.offset - self.limit
        self.next_offset = self.offset + self.limit
        if self.prev_offset < 0:
            self.prev_offset = None
        if self.next_offset >= self.total:
            self.next_offset = None

        # django
        self.page_size = self.limit
        self.this_page = django_page(self.limit, self.offset)
        self.prev_page = u''
        self.next_page = u''
        # django pagination
        self.page_start = (self.this_page - 1) * self.page_size
        self.page_next = self.this_page * self.page_size
        self.pad_before = range(0, self.page_start)
        self.pad_after = range(self.page_next, self.total)
    
    def __repr__(self):
        try:
            q = self.params.dict()
        except:
            q = dict(self.params)
        if self.total:
            return u"<SearchResults [%s-%s/%s] %s>" % (
                self.offset, self.offset + self.limit, self.total, q
            )
        return u"<SearchResults [%s] %s>" % (self.total, q)

    def _make_prevnext_url(self, query, request):
        if request:
            # some rg_* browse values withspaces e.g. "short stories"
            # are not properly quoted
            path_info = request.path_info
            if ' ' in path_info:
                path_info = path_info.replace(' ', '%20')
            return urlunsplit([
                request.scheme,
                request.META.get('HTTP_HOST', 'testserver'),
                path_info,
                query,
                None,
            ])
        return '?%s' % quote(query)
    
    def to_dict(self, format_functions):
        """Express search results in API and Redis-friendly structure
        
        @param format_functions: dict
        returns: dict
        """
        return self._dict(
            deepcopy(self.params), {}, format_functions
        )
    
    def ordered_dict(self, format_functions, request, pad=False):
        """Express search results in API and Redis-friendly structure
        
        @param format_functions: dict
        returns: OrderedDict
        """
        return self._dict(
            deepcopy(self.params), OrderedDict(), format_functions, request, pad
        )
    
    def _dict(self, params, data, format_functions, request=None, pad=False):
        """
        @param params: dict
        @param data: dict
        @param format_functions: dict
        @param pad: bool
        """
        data['total'] = self.total
        data['limit'] = self.limit
        data['offset'] = self.offset
        data['prev_offset'] = self.prev_offset
        data['next_offset'] = self.next_offset
        data['page_size'] = self.page_size
        data['this_page'] = self.this_page
        data['num_this_page'] = len(self.objects)
        if params.get('page'): params.pop('page')
        if params.get('limit'): params.pop('limit')
        if params.get('offset'): params.pop('offset')
        data['prev_api'] = ''
        data['next_api'] = ''
        data['objects'] = []
        data['query'] = self.query
        data['aggregations'] = self.aggregations
        
        # pad before
        if pad:
            data['objects'] += [{'n':n} for n in range(0, self.page_start)]
        # page
        for o in self.objects:
            format_function = format_functions[o.meta.index]
            data['objects'].append(
                format_function(
                    document=o.to_dict(),
                    request=request,
                    listitem=True,
                )
            )
        # pad after
        if pad:
            data['objects'] += [{'n':n} for n in range(self.page_next, self.total)]
        
        # API prev/next
        if self.prev_offset != None:
            data['prev_api'] = self._make_prevnext_url(
                u'limit=%s&offset=%s' % (
                    self.limit, self.prev_offset
                ),
                request
            )
        if self.next_offset != None:
            data['next_api'] = self._make_prevnext_url(
                u'limit=%s&offset=%s' % (
                    self.limit, self.next_offset
                ),
                request
            )
        
        return data


def sanitize_input(text):
    """Escape special characters
    
    http://lucene.apache.org/core/old_versioned_docs/versions/2_9_1/queryparsersyntax.html
    TODO Maybe elasticsearch-dsl or elasticsearch-py do this already
    """
    if isinstance(text, bool):
        return text
    
    BAD_SEARCH_CHARS = r'!+/:[\]^{}~'
    for c in BAD_SEARCH_CHARS:
        text = text.replace(c, '')
    text = text.replace('  ', ' ')
    
    # AND, OR, and NOT are used by lucene as logical operators.
    ## We need to escape these.
    # ...actually, we don't. We want these to be available.
    #for word in ['AND', 'OR', 'NOT']:
    #    escaped_word = "".join(["\\" + letter for letter in word])
    #    text = re.sub(
    #        r'\s*\b({})\b\s*'.format(word),
    #        r" {} ".format(escaped_word),
    #        text
    #    )
    
    # Escape odd quotes
    quote_count = text.count('"')
    if quote_count % 2 == 1:
        text = re.sub(r'(.*)"(.*)', r'\1\"\2', text)
    return text

class Searcher(object):
    """Wrapper around elasticsearch_dsl.Search
    
    >>> s = Searcher(index)
    >>> s.prep(request_data)
    'ok'
    >>> r = s.execute()
    'ok'
    >>> d = r.to_dict(request)
    """
    params = {}
    
    def __init__(self, conn=docstore.Docstore().es, search=None):
        """
        @param conn: elasticsearch.Elasticsearch with hosts/port
        @param index: str Elasticsearch index name
        """
        self.conn = conn
        self.s = search
        fields = []
        params = {}
        q = OrderedDict()
        query = {}
    
    def __repr__(self):
        return u"<Searcher '%s', %s>" % (
            es_host_name(self.conn), self.params
        )

    def prepare(self, params={}, params_whitelist=SEARCH_PARAM_WHITELIST, search_models=SEARCH_MODELS, sort=[], fields=SEARCH_INCLUDE_FIELDS, fields_nested=SEARCH_NESTED_FIELDS, fields_agg=SEARCH_AGG_FIELDS):
        """Assemble elasticsearch_dsl.Search object
        
        @param params:           dict
        @param params_whitelist: list Accept only these (SEARCH_PARAM_WHITELIST)
        @param search_models:    list Limit to these ES doctypes (SEARCH_MODELS)
        @param sort:             list of legal Elasticsearch DSL sort arguments
        @param fields:           list Retrieve these fields (SEARCH_INCLUDE_FIELDS)
        @param fields_nested:    list See SEARCH_NESTED_FIELDS
        @param fields_agg:       dict See SEARCH_AGG_FIELDS
        @returns: 
        """

        # gather inputs ------------------------------
        
        # self.params is a copy of the params arg as it was passed
        # to the method.  It is used for informational purposes
        # and is passed to SearchResults.
        # Sanitize while copying.
        if params:
            self.params = {
                key: sanitize_input(val)
                for key,val in params.items()
            }
        params = deepcopy(self.params)
        
        # scrub fields not in whitelist
        bad_fields = [
            key for key in params.keys()
            if key not in params_whitelist + ['page']
        ]
        for key in bad_fields:
            params.pop(key)
        
        indices = search_models
        if params.get('models'):
            indices = ','.join([
                docstore.Docstore().index_name(model) for model in models
            ])
        
        s = Search(using=self.conn, index=indices)
        
        # only show ResourceGuide items
        if 'encycarticle' in indices:
            s = s.filter('term', published_rg=True)
        
        if params.get('match_all'):
            s = s.query('match_all')
        elif params.get('fulltext'):
            fulltext = params.pop('fulltext')
            # MultiMatch chokes on lists
            if isinstance(fulltext, list) and (len(fulltext) == 1):
                fulltext = fulltext[0]
            # fulltext search
            s = s.query(
                QueryString(
                    query=fulltext,
                    fields=fields,
                    analyze_wildcard=False,
                    allow_leading_wildcard=False,
                    default_operator='AND',
                )
            )

        if params.get('parent'):
            parent = params.pop('parent')
            if isinstance(parent, list) and (len(parent) == 1):
                parent = parent[0]
            if parent:
                parent = '%s*' % parent
            s = s.query("wildcard", id=parent)

        # filters
        for key,val in params.items():
            
            if key in fields_nested:
                # Instead of nested search on topics.id or facility.id
                # search on denormalized topics_id or facility_id fields.
                fieldname = '%s_id' % key
                s = s.filter('term', **{fieldname: val})
    
                ## search for *ALL* the topics (AND)
                #for term_id in val:
                #    s = s.filter(
                #        Q('bool',
                #          must=[
                #              Q('nested',
                #                path=key,
                #                query=Q('term', **{'%s.id' % key: term_id})
                #              )
                #          ]
                #        )
                #    )
                
                ## search for *ANY* of the topics (OR)
                #s = s.query(
                #    Q('bool',
                #      must=[
                #          Q('nested',
                #            path=key,
                #            query=Q('terms', **{'%s.id' % key: val})
                #          )
                #      ]
                #    )
                #)
    
            elif (key in params_whitelist) and val:
                s = s.filter('term', **{key: val})
                # 'term' search is for single choice, not multiple choice fields(?)
        
        # sorting
        if sort:
            s = s.sort(*sort)
        
        # aggregations
        for fieldname,field in fields_agg.items():
            
            # nested aggregation (Elastic docs: https://goo.gl/xM8fPr)
            if fieldname == 'topics':
                s.aggs.bucket('topics', 'nested', path='topics') \
                      .bucket('topics_ids', 'terms', field='topics.id', size=1000)
            elif fieldname == 'facility':
                s.aggs.bucket('facility', 'nested', path='facility') \
                      .bucket('facility_ids', 'terms', field='facility.id', size=1000)
                # result:
                # results.aggregations['topics']['topic_ids']['buckets']
                #   {u'key': u'69', u'doc_count': 9}
                #   {u'key': u'68', u'doc_count': 2}
                #   {u'key': u'62', u'doc_count': 1}
            
            # simple aggregations
            else:
                s.aggs.bucket(fieldname, 'terms', field=field)
        
        self.s = s
    
    def execute(self, limit, offset):
        """Execute a query and return SearchResults
        
        @param limit: int
        @param offset: int
        @returns: SearchResults
        """
        if not self.s:
            raise Exception('Searcher has no ES Search object.')
        start,stop = start_stop(limit, offset)
        response = self.s[start:stop].execute()
        for n,hit in enumerate(response.hits):
            hit.index = '%s %s/%s' % (n, int(offset)+n, response.hits.total)
        return SearchResults(
            params=self.params,
            query=self.s.to_dict(),
            results=response,
            limit=limit,
            offset=offset,
        )


def search(hosts, models=[], parent=None, filters=[], fulltext='', limit=10000, offset=0, page=None, aggregations=False):
    """Fulltext search using Elasticsearch query_string syntax.
    
    Note: More approachable, higher-level function than DDR.docstore.search.
    
    Full-text search strings:
        fulltext="seattle"
        fulltext="fusa OR teruo"
        fulltext="fusa AND teruo"
        fulltext="+fusa -teruo"
        fulltext="title:seattle"
    
    Note: Quoting inside strings is not (yet?) supported in the
    command-line version.
    
    Specify parent object and doctype/model:
        parent="ddr-densho-12"
        parent="ddr-densho-1000-1-"
        doctypes=['entity','segment']
    
    Filter on certain fields (filters may repeat):
        filter=['topics:373,27']
        filter=['topics:373', 'facility=12']
    
    @param hosts dict: settings.DOCSTORE_HOST
    @param models list: Restrict to one or more models.
    @param parent str: ID of parent object (partial OK).
    @param filters list: Filter on certain fields (FIELD:VALUE,VALUE,...).
    @param fulltext str: Fulltext search query.
    @param limit int: Results page size.
    @param offset int: Number of initial results to skip (use with limit).
    @param page int: Which page of results to show.
    """
    if not models:
        models = SEARCH_MODELS
        
    if filters:
        data = {}
        for f in filters:
            field,v = f.split(':')
            values = v.split(',')
            data[field] = values
        filters = data
    else:
        filters = {}
        
    if page and offset:
        Exception("Error: Specify either offset OR page, not both.")
    if page:
        thispage = int(page)
        offset = es_offset(limit, thispage)
    
    searcher = Searcher()
    searcher.prepare(params={
        'fulltext': fulltext,
        'models': models,
        'parent': parent,
        'filters': filters,
    })
    results = searcher.execute(limit, offset)
    return results
