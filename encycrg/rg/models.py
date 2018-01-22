# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from future.utils import python_2_unicode_compatible
from builtins import str
from builtins import object
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)
import os

from elasticsearch.exceptions import NotFoundError, TransportError
from elasticsearch_dsl import Index
from elasticsearch_dsl import DocType, InnerObjectWrapper, analysis
from elasticsearch_dsl import String, Date, Nested, Boolean
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.utils import AttrList

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from rest_framework.reverse import reverse as api_reverse

from . import search

DOCTYPE_CLASS = {}  # Maps doctype names to classes

SEARCH_LIST_FIELDS = []

# set default hosts and index
connections.create_connection(hosts=settings.DOCSTORE_HOSTS)
index = Index(settings.DOCSTORE_INDEX)

"""

from elasticsearch_dsl.connections import connections
from django.conf import settings
from elasticsearch_dsl import Index
from elasticsearch_dsl import DocType, String, Date, Nested, Boolean, analysis
from elasticsearch_dsl import Search
MAX_SIZE = 10000

connections.create_connection(hosts=settings.DOCSTORE_HOSTS)
index = Index(settings.DOCSTORE_INDEX)

s = Search(doc_type='articles')[0:MAX_SIZE]
s = s.sort('title_sort')
s = s.fields([
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
    'categories',
])
response = s.execute()

"""

def hitvalue(hit, field, is_list=False):
    """
    For some reason, Search hit objects wrap values in lists.
    returns the value inside the list.
    """
    if not hasattr(hit, field):
        if is_list:
            return []
        return None
    value = getattr(hit, field)
    if isinstance(value, AttrList):
        value = list(value)
    if value and isinstance(value, list) and not is_list:
        value = value[0]
    return value


AUTHOR_LIST_FIELDS = [
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
]

@python_2_unicode_compatible
class Author(DocType):
    """
    IMPORTANT: uses Elasticsearch-DSL, not the Django ORM.
    """
    url_title = String(index='not_analyzed')  # Elasticsearch id
    public = Boolean()
    published = Boolean()
    modified = Date()
    mw_api_url = String(index='not_analyzed')
    title_sort = String(index='not_analyzed')
    title = String()
    body = String()
    article_titles = String(index='not_analyzed', multi=True)
    
    class Meta(object):
        index = settings.DOCSTORE_INDEX
        doc_type = 'authors'
    
    def __repr__(self):
        return u"<Author '%s'>" % self.url_title
    
    def __str__(self):
        return self.title

    def absolute_url(self):
        return reverse('rg-author', args=([self.title,]))
    
    @staticmethod
    def dict_list(hit, request):
        """Structure a search results hit for listing
        
        @param hit: elasticsearch_dsl.result.Result
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = hit.url_title
        data['doctype'] = hit.meta.doc_type
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-author',
            args=([hit.url_title]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-author', args=([hit.url_title]),
            request=request,
        )
        return data

    def to_dict_list(self, request=None):
        """Structure an Author for presentation in a SearchResults list
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = self.url_title
        data['doctype'] = u'authors'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-author',
            args=([self.url_title]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-author', args=([self.url_title]),
            request=request,
        )
        return data
    
    def dict_all(self, request=None):
        """Return a dict with all Author fields
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        def setval(self, data, fieldname):
            data[fieldname] = hitvalue(self, fieldname)
        
        # basic data from list
        data = self.to_dict_list(request)
        data['articles'] = []
        # fill in
        setval(self, data, 'title')
        setval(self, data, 'title_sort')
        #url_title
        setval(self, data, 'modified')
        #mw_api_url
        setval(self, data, 'body')
        # overwrite
        data['articles'] = [
            {
                'json': api_reverse('rg-api-article', args=([url_title]), request=request),
                'html': api_reverse('rg-article', args=([url_title]), request=request),
                'title': url_title,
            }
            for url_title in self.article_titles
        ]
        return data
    
    def articles(self):
        """Returns list of published light Pages for this Author.
        
        @returns: list
        """
        return [
            page
            for page in Page.pages()
            if page.url_title in self.article_titles
        ]

    @staticmethod
    def authors(num_columns=None):
        """Returns list of published light Author objects.
        
        @returns: list
        """
        KEY = 'encyc-front:authors'
        TIMEOUT = 60*5
        data = cache.get(KEY)
        if not data:
            s = Search(doc_type='authors')[0:settings.MAX_SIZE]
            s = s.sort('title_sort')
            s = s.fields(AUTHOR_LIST_FIELDS)
            response = s.execute()
            data = [
                Author(
                    url_title  = hitvalue(hit, 'url_title'),
                    title      = hitvalue(hit, 'title'),
                    title_sort = hitvalue(hit, 'title_sort'),
                    published  = hitvalue(hit, 'published'),
                    modified   = hitvalue(hit, 'modified'),
                )
                for hit in response
                if hitvalue(hit, 'published')
            ]
            cache.set(KEY, data, TIMEOUT)
        if num_columns:
            return _columnizer(data, num_columns)
        return data

    def scrub(self):
        """Removes internal editorial markers.
        Must be run on a full (non-list) Page object.
        TODO Should this happen upon import from MediaWiki?
        """
        if hasattr(self,'body') and self.body:
            self.body = str(remove_status_markers(BeautifulSoup(self.body)))

DOCTYPE_CLASS['author'] = Author
DOCTYPE_CLASS['authors'] = Author


PAGE_LIST_FIELDS = [
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
    'categories',
    'rg_rgmediatype',
    'rg_interestlevel',
]

# fields for browsing
# fields for search aggregations
PAGE_BROWSABLE_FIELDS = {
    'rg_rgmediatype': 'Media Type',
    'rg_interestlevel': 'Interest Level',
    'rg_readinglevel': 'Reading Level',
    'rg_theme': 'Theme',
    'rg_genre': 'Genre',
    'rg_relatedevents': 'Related Events',
    'rg_availability': 'Availability',
    'rg_freewebversion': 'Free Web Version',
    #'rg_denshotopic': 'Topic',
    'rg_geography': 'Geography',
    #'rg_facility': 'Facility',
    'rg_hasteachingaids': 'Has Teaching Aids',
}

PAGE_SEARCH_FIELDS = [x for x in PAGE_BROWSABLE_FIELDS.keys()]
PAGE_SEARCH_FIELDS.insert(0, 'fulltext')


@python_2_unicode_compatible
class Page(DocType):
    """
    IMPORTANT: uses Elasticsearch-DSL, not the Django ORM.
    """
    url_title = String(index='not_analyzed')  # Elasticsearch id
    public = Boolean()
    published = Boolean()
    modified = Date()
    mw_api_url = String(index='not_analyzed')
    title_sort = String(index='not_analyzed')
    title = String()
    body = String()
    prev_page = String(index='not_analyzed')
    next_page = String(index='not_analyzed')
    categories = String(index='not_analyzed', multi=True)
    coordinates = String(index='not_analyzed', multi=True)
    source_ids = String(index='not_analyzed', multi=True)
    authors_data = Nested(
        properties={
            'display': String(index='not_analyzed', multi=True),
            'parsed': String(index='not_analyzed', multi=True),
        }
    )
    
    rg_rgmediatype = String(index='not_analyzed', multi=True)
    rg_title = String()
    rg_creators = String(multi=True)
    rg_interestlevel = String(index='not_analyzed', multi=True)
    rg_readinglevel = String(index='not_analyzed', multi=True)
    rg_theme = String(index='not_analyzed', multi=True)
    rg_genre = String(index='not_analyzed', multi=True)
    rg_pov = String()
    rg_relatedevents = String()
    rg_availability = String(index='not_analyzed')
    rg_freewebversion = String(index='not_analyzed')
    #rg_denshotopic = String(index='not_analyzed', multi=True)
    rg_geography = String(index='not_analyzed', multi=True)
    #rg_facility = String(index='not_analyzed', multi=True)
    rg_chronology = String(index='not_analyzed', multi=True)
    rg_hasteachingaids = String(index='not_analyzed')
    rg_warnings = String()
    #rg_primarysecondary = String(index='not_analyzed', multi=True)
    #rg_lexile = String(index='not_analyzed', multi=True)
    #rg_guidedreadinglevel = String(index='not_analyzed', multi=True)
    
    class Meta(object):
        index = settings.DOCSTORE_INDEX
        doc_type = u'articles'
    
    def __repr__(self):
        return u"<Page '%s'>" % self.url_title
    
    def __str__(self):
        return self.url_title
    
    def absolute_url(self):
        return reverse('rg-page', args=([self.title]))
    
    def encyclopedia_url(self):
        return os.path.join(settings.ENCYCLOPEDIA_URL, self.title)
    
    @staticmethod
    def dict_list(hit, request):
        """Structure a search results hit for listing
        
        @param hit: elasticsearch_dsl.result.Result
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        hit_dict = hit.__dict__
        data['id'] = hit.url_title
        data['doctype'] = hit.meta.doc_type
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-article',
            args=([hit.url_title]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-article',
            args=([hit.url_title]),
            request=request
        )
        return data

    def to_dict_list(self, request=None):
        """Structure a Page for presentation in a SearchResults list
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data=OrderedDict()
        data['id'] = self.url_title
        data['doctype'] = u'articles'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-article',
            args=([self.url_title]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-article',
            args=([self.url_title]),
            request=request,
        )
        data['title_sort'] = self.title_sort
        
        def setval(self, data, fieldname, is_list=False):
            data[fieldname] = hitvalue(self, fieldname, is_list)
        
        setval(self, data, 'rg_rgmediatype', is_list=1)
        setval(self, data, 'rg_interestlevel', is_list=1)
        return data
    
    def dict_all(self, request=None):
        """Return a dict with all Page fields
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        def setval(self, data, fieldname, is_list=False):
            data[fieldname] = hitvalue(self, fieldname, is_list)
        
        # basic data from list
        data = self.to_dict_list(request)
        # put these at the top because OrderedDict
        data['categories'] = []
        data['topics'] = []
        data['authors'] = []
        data['sources'] = []
        # fill in
        setval(self, data, 'title')
        setval(self, data, 'title_sort')
        #url_title
        #prev_page
        #next_page
        setval(self, data, 'categories')
        setval(self, data, 'source_ids')
        #public
        #published
        setval(self, data, 'modified')
        #mw_api_url
        setval(self, data, 'coordinates')
        #self, 'authors_data'
        setval(self, data, 'rg_rgmediatype', is_list=1)
        setval(self, data, 'rg_title')
        setval(self, data, 'rg_creators')
        setval(self, data, 'rg_interestlevel', is_list=1)
        setval(self, data, 'rg_readinglevel', is_list=1)
        setval(self, data, 'rg_theme', is_list=1)
        setval(self, data, 'rg_genre', is_list=1)
        setval(self, data, 'rg_pov', is_list=1)
        setval(self, data, 'rg_relatedevents', is_list=1)
        setval(self, data, 'rg_availability', is_list=1)
        setval(self, data, 'rg_freewebversion', is_list=1)
        #setval(self, data, 'rg_denshotopic')
        setval(self, data, 'rg_geography', is_list=1)
        #setval(self, data, 'rg_facility')
        setval(self, data, 'rg_chronology', is_list=1)
        setval(self, data, 'rg_hasteachingaids', is_list=1)
        setval(self, data, 'rg_warnings', is_list=1)
        setval(self, data, 'body')
        # overwrite
        data['categories'] = [
            {
                'json': api_reverse('rg-api-category', args=([category]), request=request),
                'html': api_reverse('rg-category', args=([category]), request=request),
                'title': category,
            }
            for category in self.categories
        ]
        #'ddr_topic_terms': topic_term_ids,
        data['sources'] = [
            {
                'json': api_reverse('rg-api-source', args=([source_id]), request=request),
                'html': api_reverse('rg-source', args=([source_id]), request=request),
                'id': source_id,
            }
            for source_id in self.source_ids
        ]
        data['authors'] = [
            {
                'json': api_reverse('rg-api-author', args=([author_titles]), request=request),
                'html': api_reverse('rg-author', args=([author_titles]), request=request),
                'title': author_titles,
            }
            for author_titles in self.authors_data['display']
        ]
        return data

    def authors(self):
        """Returns list of published light Author objects for this Page.
        
        @returns: list
        """
        objects = []
        if self.authors_data:
            for url_title in self.authors_data['display']:
                try:
                    author = Author.get(url_title)
                except NotFoundError:
                    author = url_title
                objects.append(author)
        return objects

    def first_letter(self):
        return self.title_sort[0]

    @staticmethod
    def search():
        """RG-only Page Search
        
        @returns: elasticsearch_dsl.Search
        """
        s = search.Search().doc_type(Page)
        s = s.filter('exists', field='rg_rgmediatype')
        return s
    
    @staticmethod
    def pages(only_rg=True, start=0, stop=settings.MAX_SIZE):
        """Returns list of published light Page objects.
        
        @param only_rg: boolean Only return RG pages (rg_rgmediatype present)
        @returns: list
        """
        s = Page.search()
        if only_rg:
            # require rg_rgmediatype
            s = s.filter(Q('exists', field=['rg_rgmediatype']))
        s = s.sort('title_sort')
        s = s.fields(PAGE_LIST_FIELDS)
        query = s.to_dict()
        count = s.count()
        if (start != 0) or (stop != settings.MAX_SIZE):
            s = s[start:stop]
        results = s.execute()
        
        return search.SearchResults(
            mappings=DOCTYPE_CLASS,
            query=query,
            count=count,
            results=results,
            #limit=limit,
            #offset=offset,
        ).objects
    
    @staticmethod
    def pages_by_category():
        """Returns list of (category, Pages) tuples, alphabetical by category
        
        @returns: list
        """
        KEY = u'encyc-front:pages_by_category'
        TIMEOUT = 60*5
        data = cache.get(KEY)
        if not data:
            categories = {}
            for page in Page.pages():
                for category in page.categories:
                    # exclude internal editorial categories
                    if category not in settings.MEDIAWIKI_HIDDEN_CATEGORIES:
                        if category not in list(categories.keys()):
                            categories[category] = []
                        # pages already sorted so category lists will be sorted
                        if page not in categories[category]:
                            categories[category].append(page)
            data = [
                (key,categories[key])
                for key in sorted(categories.keys())
            ]
            cache.set(KEY, data, TIMEOUT)
        return data

    def scrub(self):
        """remove internal editorial markers.
        
        Must be run on a full (non-list) Page object.
        TODO Should this happen upon import from MediaWiki?
        """
        if hasattr(self,'body') and self.body:
            self.body = str(remove_status_markers(BeautifulSoup(self.body)))
    
    def sources(self):
        """Returns list of published light Source objects for this Page.
        
        @returns: list
        """
        try:
            return Source.mget(self.source_ids, missing='skip')
        except TransportError as err:
            if err.status_code == 400:
                return []
            raise err
    
    def topics(self):
        """List of DDR topics associated with this page.
        
        @returns: list
        """
        # return list of dicts rather than an Elasticsearch results object
        terms = []
        #for t in Elasticsearch.topics_by_url().get(self.absolute_url(), []):
        #    term = {
        #        key: val
        #        for key,val in list(t.items())
        #    }
        #    term.pop('encyc_urls')
        #    term['ddr_topic_url'] = u'%s/%s/' % (
        #        settings.DDR_TOPICS_BASE,
        #        term['id']
        #    )
        #    terms.append(term)
        return terms
    
    def ddr_terms_objects(self, size=100):
        """Get dict of DDR objects for article's DDR topic terms.
        
        Ironic: this uses DDR's REST UI rather than ES.
        """
        if not hasattr(self, '_related_terms_docs'):
            terms = self.topics()
            objects = ddr.related_by_topic(
                term_ids=[term['id'] for term in terms],
                size=size
            )
            for term in terms:
                term['objects'] = objects[term['id']]
        return terms
    
    def ddr_objects(self, size=5):
        """Get list of objects for terms from DDR.
        
        Ironic: this uses DDR's REST UI rather than ES.
        """
        objects = ddr.related_by_topic(
            term_ids=[term['id'] for term in self.topics()],
            size=size
        )
        return ddr._balance(objects, size)

DOCTYPE_CLASS['article'] = Page
DOCTYPE_CLASS['articles'] = Page


SOURCE_LIST_FIELDS = [
    'encyclopedia_id',
    'published',
    'modified',
    'headword',
    'media_format',
    'img_path',
]

@python_2_unicode_compatible
class Source(DocType):
    """
    IMPORTANT: uses Elasticsearch-DSL, not the Django ORM.
    """
    encyclopedia_id = String(index='not_analyzed')  # Elasticsearch id
    densho_id = String(index='not_analyzed')
    psms_id = String(index='not_analyzed')
    psms_api_uri = String(index='not_analyzed')
    institution_id = String(index='not_analyzed')
    collection_name = String(index='not_analyzed')
    created = Date()
    modified = Date()
    published = Boolean()
    creative_commons = Boolean()
    headword = String(index='not_analyzed')
    #original_path = String(index='not_analyzed')
    original_url = String(index='not_analyzed')  # TODO use original_path
    #streaming_path = String(index='not_analyzed')
    #rtmp_path = String(index='not_analyzed')
    streaming_url = String(index='not_analyzed')  # TODO remove
    external_url = String(index='not_analyzed')
    media_format = String(index='not_analyzed')
    aspect_ratio = String(index='not_analyzed')
    original_size = String(index='not_analyzed')
    display_size = String(index='not_analyzed')
    display = String(index='not_analyzed')
    caption = String()
    caption_extended = String()
    #transcript_path = String(index='not_analyzed')
    transcript = String()  # TODO remove
    courtesy = String(index='not_analyzed')
    filename = String(index='not_analyzed')
    img_path = String(index='not_analyzed')
    
    class Meta(object):
        index = settings.DOCSTORE_INDEX
        doc_type = u'sources'
    
    def __repr__(self):
        return u"<Source '%s'>" % self.encyclopedia_id
    
    def __str__(self):
        return self.encyclopedia_id
    
    def absolute_url(self):
        return reverse('rg-source', args=([self.encyclopedia_id]))
    
    def img_url(self):
        return os.path.join(settings.MEDIA_URL, self.img_path)
    
    def img_url_local(self):
        return os.path.join(settings.MEDIA_URL_LOCAL, self.img_path)
    
    #def streaming_url(self):
    #    return os.path.join(settings.SOURCES_MEDIA_URL, self.streaming_path)
    
    def transcript_url(self):
        if self.transcript_path():
            return os.path.join(settings.SOURCES_MEDIA_URL, self.transcript_path())

    @staticmethod
    def dict_list(hit, request):
        """Structure a search results hit for listing
        
        @param hit: elasticsearch_dsl.result.Result
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = hit.encyclopedia_id
        data['doctype'] = hit.meta.doc_type
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-source',
            args=([hit.encyclopedia_id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-source', args=([hit.encyclopedia_id]),
            request=request,
        )
        return data

    def to_dict_list(self, request=None):
        """Structure a Source for presentation in a SearchResults list
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = self.encyclopedia_id
        data['doctype'] = u'sources'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-source',
            args=([self.encyclopedia_id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-source',
            args=([self.encyclopedia_id]),
            request=request,
        )
        return data

    def dict_all(self, request=None):
        """Return a dict with all Source fields
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        def setval(self, data, fieldname):
            data[fieldname] = hitvalue(self, fieldname)
        
        # basic data from list
        data = self.to_dict_list(request)
        # put these at the top because OrderedDict
        # fill in
        setval(self, data, 'encyclopedia_id')
        setval(self, data, 'densho_id')
        setval(self, data, 'psms_id')
        setval(self, data, 'institution_id')
        setval(self, data, 'collection_name')
        setval(self, data, 'created')
        setval(self, data, 'modified')
        setval(self, data, 'creative_commons')
        setval(self, data, 'headword')
        setval(self, data, 'streaming_url')
        setval(self, data, 'external_url')
        setval(self, data, 'media_format')
        setval(self, data, 'aspect_ratio')
        setval(self, data, 'original_size')
        setval(self, data, 'display_size')
        setval(self, data, 'display')
        setval(self, data, 'caption')
        setval(self, data, 'caption_extended')
        setval(self, data, 'transcript')
        setval(self, data, 'courtesy')
        setval(self, data, 'filename')
        setval(self, data, 'img_path')
        return data
    
    def original_path(self):
        if self.original_url:
            return os.path.join(
                settings.SOURCES_MEDIA_BUCKET,
                os.path.basename(self.original_url)
            )
        return None

    def rtmp_path(self):
        return self.streaming_url
    
    def streaming_path(self):
        if self.streaming_url:
            return os.path.join(
                settings.SOURCES_MEDIA_BUCKET,
                os.path.basename(self.streaming_url)
            )
        return None
    
    def transcript_path(self):
        if self.transcript:
            return os.path.join(
                settings.SOURCES_MEDIA_BUCKET,
                os.path.basename(self.transcript)
            )
        return None
    
    def article(self):
        if self.headword:
            try:
                page = Page.get(self.headword)
            except NotFoundError:
                page = None
        return page
    
    @staticmethod
    def sources():
        """Returns list of published light Source objects.
        
        @returns: list
        """
        KEY = u'encyc-front:sources'
        TIMEOUT = 60*5
        data = cache.get(KEY)
        if not data:
            s = Search(doc_type='sources')[0:settings.MAX_SIZE]
            s = s.sort('encyclopedia_id')
            s = s.fields(SOURCE_LIST_FIELDS)
            response = s.execute()
            data = [
                Source(
                    encyclopedia_id = hitvalue(hit, 'encyclopedia_id'),
                    published = hitvalue(hit, 'published'),
                    modified = hitvalue(hit, 'modified'),
                    headword = hitvalue(hit, 'headword'),
                    media_format = hitvalue(hit, 'media_format'),
                    img_path = hitvalue(hit, 'img_path'),
                   )
                for hit in response
                if hitvalue(hit, 'published')
            ]
            cache.set(KEY, data, TIMEOUT)
        return data


@python_2_unicode_compatible
class Citation(object):
    """Represents a citation for a MediaWiki page.
    IMPORTANT: not a Django model object!
    """
    url_title = None
    url = None
    page_url = None
    cite_url = None
    href = None
    status_code = None
    error = None
    title = None
    lastmod = None
    retrieved = None
    authors = []
    authors_apa = ''
    authors_bibtex = ''
    authors_chicago = ''
    authors_cse = ''
    authors_mhra = ''
    authors_mla = ''
    
    def __repr__(self):
        return u"<Citation '%s'>" % self.url_title
    
    def __str__(self):
        return self.url_title
    
    def __init__(self, page, request):
        self.uri = page.absolute_url()
        self.href = u'http://%s%s' % (request.META['HTTP_HOST'], self.uri)
        if getattr(page, 'title', None):
            self.title = page.title
        elif getattr(page, 'caption', None):
            self.title = page.caption
        if getattr(page, 'lastmod', None):
            self.lastmod = page.lastmod
        elif getattr(page, 'modified', None):
            self.lastmod = page.modified
        if getattr(page, 'authors_data', None):
            self.authors = page.authors_data
            self.authors_apa = citations.format_authors_apa(self.authors['parsed'])
            self.authors_bibtex = citations.format_authors_bibtex(self.authors['parsed'])
            self.authors_chicago = citations.format_authors_chicago(self.authors['parsed'])
            self.authors_cse = citations.format_authors_cse(self.authors['parsed'])
            self.authors_mhra = citations.format_authors_mhra(self.authors['parsed'])
            self.authors_mla = citations.format_authors_mla(self.authors['parsed'])
        self.retrieved = datetime.now()

DOCTYPE_CLASS['source'] = Source
DOCTYPE_CLASS['sources'] = Source

SEARCH_LIST_FIELDS = AUTHOR_LIST_FIELDS + PAGE_LIST_FIELDS + SOURCE_LIST_FIELDS


TERM_TITLES = {}  # values set later

FACILITY_TYPES = {}

class Location(InnerObjectWrapper):
    pass

class GeoPoint(InnerObjectWrapper):
    pass

class ELink(InnerObjectWrapper):
    pass

@python_2_unicode_compatible
class FacetTerm(DocType):
    id = String(index='not_analyzed')  # Elasticsearch id
    facet_id = String(index='not_analyzed')
    title = String()
    # topics
    _title = String()
    description = String()
    path = String(index='not_analyzed')
    parent_id = String(index='not_analyzed')
    ancestors = String(index='not_analyzed', multi=True)
    children = String(index='not_analyzed', multi=True)
    siblings = String(index='not_analyzed', multi=True)
    encyc_urls = String(index='not_analyzed', multi=True)
    weight = String()
    # facility
    type = String(index='not_analyzed')
    locations = Nested(
        doc_class=Location,
        properties={
            'label': String(),
            'geopoint': Nested(
                doc_class=GeoPoint,
                properties={
                    'lat': String(),
                    'lng': String(),
                }
            )
        }
    )
    elinks = Nested(
        doc_class=ELink,
        properties={
            'label': String(),
            'url': String(index='not_analyzed'),
        }
    )
    
    class Meta(object):
        index = settings.DOCSTORE_INDEX
        doc_type = u'facetterms'
    
    def __repr__(self):
        return u"<FacetTerm '%s-%s'>" % (self.facet_id, self.id)
    
    def __str__(self):
        return u'%s-%s' % (self.facet_id, self.id)
    
    @staticmethod
    def terms(request, facet_id=None, limit=settings.DEFAULT_LIMIT, offset=0):
        s = Search(doc_type='facetterms')[0:settings.MAX_SIZE]
        if facet_id:
            s = s.query("match", facet_id=facet_id)
            if facet_id == 'topics':
                s = s.sort('path')
            elif facet_id == 'facility':
                s = s.sort('type', 'title')
        response = s.execute()
        data = [
            FacetTerm(
                id = hitvalue(hit, 'id'),
                facet_id = hitvalue(hit, 'facet_id'),
                term_id = hitvalue(hit, 'term_id'),
                title = hitvalue(hit, 'title'),
                path = hitvalue(hit, 'path'),
                type = hitvalue(hit, 'type'),
               )
            for hit in response
        ]
        return data
    
    def to_dict_list(self, request=None):
        data = OrderedDict()
        data['id'] = self.id
        data['facet_id'] = self.facet_id
        data['term_id'] = self.facet_id
        data['doctype'] = u'facetterms'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-term',
            args=([self.id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-term',
            args=([self.id]),
            request=request,
        )
        data['path'] = self.path
        data['title'] = self.title
        data['type'] = self.type
        return data

    def dict_all(self, request=None):
        """Return a dict with all FacetTerm fields
        
        NOTE: we assume that TERM_TITLES is populated when this is called.
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = self.id
        data['facet_id'] = self.facet_id
        data['term_id'] = self.facet_id
        data['doctype'] = u'facetterms'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-term',
            args=([self.id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-term',
            args=([self.id]),
            request=request,
        )
        data['title'] = self.title
        if self.facet_id == u'topics':
            data['_title'] = self._title
            data['description'] = self.description
            data['path'] = self.path

            def term_listitem(facet_id, tid, request=None):
                term_id = '-'.join([facet_id, str(tid)])
                item = TERM_TITLES.get(term_id)
                if item:
                    title = item['title']
                    path = item['path']
                else:
                    title = term_id
                    path = ''
                d = OrderedDict()
                d['id'] = term_id
                d['json'] = api_reverse('rg-api-term', args=([u'%s-%s' % (facet_id, tid)]), request=request)
                d['html'] = api_reverse('rg-term', args=([u'%s-%s' % (facet_id, tid)]), request=request)
                d['path'] = path
                d['title'] = title
                return d
            
            if self.parent_id:
                data['parent_id'] = api_reverse('rg-api-term', args=([u'%s-%s' % (self.facet_id, self.parent_id)]), request=request)
                data['parent'] = term_listitem(self.facet_id, self.parent_id, request)
            else:
                data['parent_id'] = u''
                data['parent'] = None
            data['ancestors'] = [
                term_listitem(self.facet_id, tid, request)
                for tid in self.ancestors
            ]
            data['children'] = [
                term_listitem(self.facet_id, tid, request)
                for tid in self.children
            ]
            data['siblings'] = [
                term_listitem(self.facet_id, tid, request)
                for tid in self.siblings
            ]
            data['weight'] = self.weight
        elif self.facet_id == u'facility':
            data['type'] = self.type
            data['locations'] = []
            for n,loc in enumerate(self.locations):
                data['locations'].append( {} )
                data['locations'][n]['label'] = loc.label
                data['locations'][n]['geopoint'] = {}
                data['locations'][n]['geopoint']['lat'] = loc.geopoint.lat
                data['locations'][n]['geopoint']['lng'] = loc.geopoint.lng
        data['encyc_urls'] = []
        for n,item in enumerate(self.encyc_urls):
            d = OrderedDict()
            d['id'] = item.title.replace(u'/', u'').replace(u'%20', u' ')
            d['doctype'] = 'articles'
            d['links'] = {}
            d['links']['json'] = api_reverse('rg-api-article', args=([item.url_title]), request=request)
            d['links']['html'] = api_reverse('rg-article', args=([item.url_title]), request=request)
            data['encyc_urls'].append(d)
        return data

TERM_TITLES = {
    term.id: {
        'id': term.id,
        'title': term.title,
        'path': term.path,
    }
    for term in FacetTerm.terms(request=None)
}

def facility_types():
    types = {}
    for term in FacetTerm.terms(request=None, facet_id='facility'):
        if types.get(term.type):
            types[term.type]['count'] += 1
        else:
            types[term.type] = term.dict_all()
            types[term.type]['count'] = 1
    return types

def facility_type(type_id):
    return [
        term
        for term in FacetTerm.terms(request=None, facet_id='facility')
        if term.type == type_id
    ]




@python_2_unicode_compatible
class Facet(DocType):
    id = String(index='not_analyzed')  # Elasticsearch id
    title = String()
    description = String()
    terms = []
    
    class Meta(object):
        index = settings.DOCSTORE_INDEX
        doc_type = u'facets'
    
    def __repr__(self):
        return u"<Facet '%s'>" % self.id
    
    def __str__(self):
        return self.id
    
    def absolute_url(self):
        return reverse('rg-facet', args=([self.id]))

    @staticmethod
    def dict_list(hit, request):
        data = OrderedDict()
        data['id'] = hit.id
        data['title'] = hit.title
        data['description'] = hit.description
        return data

    def to_dict_list(self, request=None):
        data = OrderedDict()
        data['id'] = self.id
        data['doctype'] = u'facet'
        data['title'] = self.title
        data['description'] = self.description
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-facet',
            args=([self.id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-facet',
            args=([self.id]),
            request=request,
        )
        return data

    def dict_all(self, request=None):
        """Return a dict with all Facet fields
        
        @param request: django.http.request.HttpRequest
        @returns: OrderedDict
        """
        data = OrderedDict()
        data['id'] = self.id
        data['doctype'] = u'facet'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-facet',
            args=([self.id]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-facet',
            args=([self.id]),
            request=request,
        )
        data['title'] = self.title
        data['description'] = self.description
        return data

    @staticmethod
    def facets(request, limit=settings.DEFAULT_LIMIT, offset=0):
        s = Search(doc_type=u'facets')[0:settings.MAX_SIZE]
        response = s.execute()
        data = [
            Facet(
                id = hitvalue(hit, 'id'),
                title = hitvalue(hit, 'title'),
                description = hitvalue(hit, 'description'),
               )
            for hit in response
        ]
        return data
    
#    @staticmethod
#    def children(oid, request, sort=[], limit=DEFAULT_LIMIT, offset=0, raw=False):
#        LIST_FIELDS = [
#            'id',
#            'sort',
#            'title',
#            'facet',
#            'ancestors',
#            'path',
#            'type',
#        ]
#        q = docstore.search_query(
#            must=[
#                {'term': {'facet': oid}}
#            ]
#        )
#        results = docstore.Docstore().search(
#            doctypes=['facetterm'],
#            query=q,
#            sort=sort,
#            fields=LIST_FIELDS,
#            from_=offset,
#            size=limit,
#        )
#        if raw:
#            return [
#                term['_source']
#                for term in results['hits']['hits']
#            ]
#        return format_list_objects(
#            paginate_results(
#                results,
#                offset,
#                limit,
#                request
#            ),
#            request,
#            format_term
#        )
    
#    @staticmethod
#    def make_tree(terms_list):
#        """Rearranges terms list into hierarchical list.
#        
#        Uses term['ancestors'] to generate a tree structure
#        then "prints out" the tree to a list with indent (depth) indicators.
#        More specifically, it adds term['depth'] attribs and reorders
#        terms so they appear in the correct places in the hierarchy.
#        source: https://gist.github.com/hrldcpr/2012250
#        
#        @param terms_list: list
#        @returns: list
#        """
#        def tree():
#            """Define a tree data structure
#            """
#            return defaultdict(tree)
        
#        def add(tree_, path):
#            """
#            @param tree_: defaultdict
#            @param path: list of ancestor term IDs
#            """
#            for node in path:
#                tree_ = tree_[node]
        
#        def populate(terms_list):
#            """Create and populate tree structure
#            by iterating through list of terms and referencing ancestor/path keys
#            
#            @param terms_list: list of dicts
#            @returns: defaultdict
#            """
#            tree_ = tree()
#            for term in terms_list:
#                path = [tid for tid in term['ancestors']]
#                path.append(term['id'])
#                add(tree_, path)
#            return tree_
        
#        def flatten(tree_, depth=0):
#            """Takes tree dict and returns list of terms with depth values
#            
#            Variation on ptr() from the gist
#            Recursively gets term objects from terms_dict, adds depth,
#            and appends to list of terms.
#            
#            @param tree_: defaultdict Tree
#            @param depth: int Depth of indents
#            """
#            for key in sorted(tree_.keys()):
#                term = terms_dict[key]
#                term['depth'] = depth
#                terms.append(term)
#                depth += 1
#                flatten(tree_[key], depth)
#                depth -= 1
#        
#        terms_dict = {t['id']: t for t in terms_list}
#        terms_tree = populate(terms_list)
#        terms = []
#        flatten(terms_tree)
#        return terms

#    @staticmethod
#    def topics_terms(request):
#        """List of topics facet terms, with tree indents and doc counts
#        
#        TODO ES does query and aggregations caching.
#        Does caching this mean the query/aggs won't be cached in ES?
#        
#        @param request: Django request object.
#        @returns: list of Terms
#        """
#        facet_id = 'topics'
#        key = 'facet:%s:terms' % facet_id
#        cached = cache.get(key)
#        if not cached:
#            terms = Facet.children(
#                facet_id, request,
#                sort=[('title','asc')],
#                limit=10000, raw=True
#            )
#            for term in terms:
#                term['links'] = {}
#                term['links']['html'] = reverse(
#                    'ui-browse-term', args=[facet_id, term['id']]
#                )
#            terms = Facet.make_tree(terms)
#            Term.term_aggregations('topics.id', 'topics', terms, request)
#            cached = terms
#            cache.set(key, cached, settings.CACHE_TIMEOUT)
#        return cached
    
#    @staticmethod
#    def get(oid, request):
#        document = docstore.Docstore().get(
#            model='facet', document_id=oid
#        )
#        if not document:
#            raise NotFound()
#        data = format_facet(document, request)
#        HIDDEN_FIELDS = []
#        for field in HIDDEN_FIELDS:
#            pop_field(data, field)
#        return data

#    @staticmethod
#    def facility_terms(request):
#        """List of facility facet terms, sorted and with doc counts
#        
#        TODO ES does query and aggregations caching.
#        Does caching this mean the query/aggs won't be cached in ES?
#        
#        @param request: Django request object.
#        @returns: list of Terms
#        """
#        facet_id = 'facility'
#        key = 'facet:%s:terms' % facet_id
#        cached = cache.get(key)
#        if not cached:
#            terms = Facet.children(
#                facet_id, request,
#                sort=[('title','asc')],
#                limit=10000, raw=True
#            )
#            for term in terms:
#                term['links'] = {}
#                term['links']['html'] = reverse(
#                    'ui-browse-term', args=[facet_id, term['id']]
#                )
#            terms = sorted(terms, key=lambda term: term['title'])
#            Term.term_aggregations('facility.id', 'facility', terms, request)
#            cached = terms
#            cache.set(key, cached, settings.CACHE_TIMEOUT)
#        return cached


class Term(object):
    pass

#    @staticmethod
#    def terms(request, limit=DEFAULT_LIMIT, offset=0):
#        SORT_FIELDS = [
#        ]
#        LIST_FIELDS = [
#            'id',
#            'title',
#        ]
#        q = docstore.search_query(
#            must=[
#                { "match_all": {}}
#            ]
#        )
#        results = docstore.Docstore().search(
#            doctypes=['facetterm'],
#            query=q,
#            sort=SORT_FIELDS,
#            fields=LIST_FIELDS,
#            from_=offset,
#            size=limit,
#        )
#        return format_list_objects(
#            paginate_results(
#                results,
#                offset,
#                limit,
#                request
#            ),
#            request,
#            format_facet
#        )

#    @staticmethod
#    def term_aggregations(field, fieldname, terms, request):
#        """Add number of documents for each facet term
#        
#        @param field: str Field name in ES (e.g. 'topics.id')
#        @param fieldname: str Fieldname in ddrpublic (e.g. 'topics')
#        @param terms list
#        """
#        # aggregations
#        query = {
#            'models': [
#                'entity',
#                'segment',
#            ],
#            'aggs': {
#                fieldname: {
#                    'terms': {
#                        'field': field,
#                        'size': len(terms), # doc counts for all terms
#                    }
#                },
#            }
#        }
#        results = docstore_search(
#            models=query['models'],
#            aggs=query['aggs'],
#            request=request,
#        )
#        aggs = aggs_dict(results.get('aggregations'))[fieldname]
#        # assign num docs per term
#        for term in terms:
#            num = aggs.get(str(term['id']), 0) # aggs keys are str(int)s
#            term['doc_count'] = num            # could be used for sorting terms!
    
#    @staticmethod
#    def get(oid, request):
#        document = docstore.Docstore().get(
#            model='facetterm', document_id=oid
#        )
#        if not document:
#            raise NotFound()
#        # save data for breadcrumbs
#        # (we assume ancestors and path in same order)
#        facet = document['_source']['facet']
#        path = document['_source'].get('path')
#        ancestors = document['_source'].get('ancestors')
#        
#        data = format_term(document, request)
#        HIDDEN_FIELDS = []
#        for field in HIDDEN_FIELDS:
#            pop_field(data, field)
#        # breadcrumbs
#        # join path (titles) and ancestors (IDs)
#        if path and ancestors:
#            data['breadcrumbs'] = []
#            path = path.split(':')
#            path.pop() # last path item is not an ancestor
#            if len(path) == len(ancestors):
#                for n,tid in enumerate(ancestors):
#                    data['breadcrumbs'].append({
#                        'url':reverse('ui-browse-term', args=[facet, tid]),
#                        'title':path[n]
#                    })
#        return data

#    @staticmethod
#    def objects(facet_id, term_id, limit=DEFAULT_LIMIT, offset=0, request=None):
#        field = '%s.id' % facet_id
#        return docstore_search(
#            must=[
#                {'terms': {field: [term_id]}},
#            ],
#            models=[],
#            sort_fields=[
#                'sort',
#                'id',
#                'record_created',
#                'record_lastmod',
#            ],
#            limit=limit,
#            offset=offset,
#            request=request,
#        )
