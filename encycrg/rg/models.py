# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from elasticsearch_dsl import DocType, String, Date, Nested, Boolean, analysis
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.utils import AttrList

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from rest_framework.reverse import reverse as api_reverse

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

def hitvalue(hit, field):
    """
    For some reason, Search hit objects wrap values in lists.
    returns the value inside the list.
    """
    if not hasattr(hit, field):
        return None
    value = getattr(hit, field)
    if value and (isinstance(value, AttrList) or isinstance(value, list)):
        value = value[0]
    return value


AUTHOR_LIST_FIELDS = [
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
]

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
    
    class Meta:
        index = settings.DOCSTORE_INDEX
        doc_type = 'authors'
    
    def __repr__(self):
        return "<Author '%s'>" % self.url_title
    
    def __str__(self):
        return self.title

    def absolute_url(self):
        return reverse('rg-author', args=([self.title,]))
    
    @staticmethod
    def dict_list(hit, request):
        data = OrderedDict()
        data['id'] = hit['_source']['url_title']
        data['doctype'] = 'authors'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-author',
            args=([hit['_source']['url_title']]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-author', args=([hit['_source']['url_title']]),
            request=request,
        )
        return data

    def to_dict_list(self, request=None):
        data = OrderedDict()
        data['id'] = self.url_title
        data['doctype'] = 'authors'
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
    
    def dict_all(self, data=OrderedDict()):
        """Return a dict with all fields
        """
        def setval(self, data, fieldname):
            data[fieldname] = hitvalue(self, fieldname)
        
        setval(self, data, 'title')
        setval(self, data, 'title_sort')
        #url_title
        setval(self, data, 'modified')
        #mw_api_url
        setval(self, data, 'body')
        #article_titles
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
            self.body = unicode(remove_status_markers(BeautifulSoup(self.body)))

DOCTYPE_CLASS['author'] = Author
DOCTYPE_CLASS['authors'] = Author


PAGE_LIST_FIELDS = [
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
    'categories',
]

PAGE_BROWSABLE_FIELDS = [
    'rg_rgmediatype',
    'rg_interestlevel',
    'rg_readinglevel',
    'rg_theme',
    'rg_genre',
    'rg_relatedevents',
    'rg_availability',
    'rg_freewebversion',
    'rg_denshotopic',
    'rg_geography',
    'rg_facility',
    'rg_hasteachingaids',
]

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
    rg_denshotopic = String(index='not_analyzed', multi=True)
    rg_geography = String(index='not_analyzed', multi=True)
    rg_facility = String(index='not_analyzed', multi=True)
    rg_chronology = String(index='not_analyzed', multi=True)
    rg_hasteachingaids = String(index='not_analyzed')
    rg_warnings = String()
    #rg_primarysecondary = String(index='not_analyzed', multi=True)
    #rg_lexile = String(index='not_analyzed', multi=True)
    #rg_guidedreadinglevel = String(index='not_analyzed', multi=True)
    
    class Meta:
        index = settings.DOCSTORE_INDEX
        doc_type = 'articles'
    
    def __repr__(self):
        return "<Page '%s'>" % self.url_title
    
    def __str__(self):
        return self.url_title
    
    def absolute_url(self):
        return reverse('rg-page', args=([self.title]))
    
    @staticmethod
    def dict_list(hit, request):
        data = OrderedDict()
        data['id'] = hit['_source']['url_title']
        data['doctype'] = 'articles'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-api-article',
            args=([hit['_source']['url_title']]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-article',
            args=([hit['_source']['url_title']]),
            request=request
        )
        return data

    def to_dict_list(self, request=None):
        data = OrderedDict()
        data['id'] = self.url_title
        data['doctype'] = 'articles'
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
        return data
    
    def dict_all(self, data=OrderedDict()):
        """Return a dict with all fields
        """
        def setval(self, data, fieldname):
            data[fieldname] = hitvalue(self, fieldname)
        
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
        setval(self, data, 'rg_rgmediatype')
        setval(self, data, 'rg_title')
        setval(self, data, 'rg_creators')
        setval(self, data, 'rg_interestlevel')
        setval(self, data, 'rg_readinglevel')
        setval(self, data, 'rg_theme')
        setval(self, data, 'rg_genre')
        setval(self, data, 'rg_pov')
        setval(self, data, 'rg_relatedevents')
        setval(self, data, 'rg_availability')
        setval(self, data, 'rg_freewebversion')
        setval(self, data, 'rg_denshotopic')
        setval(self, data, 'rg_geography')
        setval(self, data, 'rg_facility')
        setval(self, data, 'rg_chronology')
        setval(self, data, 'rg_hasteachingaids')
        setval(self, data, 'rg_warnings')
        setval(self, data, 'body')
        return data

    def authors(self):
        """Returns list of published light Author objects for this Page.
        
        @returns: list
        """
        objects = []
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
    def pages(only_rg=True):
        """Returns list of published light Page objects.
        
        @param only_rg: boolean Only return RG pages (rg_rgmediatype present)
        @returns: list
        """
        KEY = 'encyc-front:pages'
        TIMEOUT = 60*5
        #data = cache.get(KEY)
        data = None
        if not data:
            s = Search().doc_type(Page)[0:settings.MAX_SIZE]
            if only_rg:
                # require rg_rgmediatype
                s = s.filter(Q('exists', field=['rg_rgmediatype']))
            s = s.sort('title_sort')
            s = s.fields(PAGE_LIST_FIELDS)
            response = s.execute()
            data = []
            for hit in response:
                if hitvalue(hit, 'published'):
                    data.append(Page(
                        url_title  = hitvalue(hit, 'url_title'),
                        title      = hitvalue(hit, 'title'),
                        title_sort = hitvalue(hit, 'title_sort'),
                        published  = hitvalue(hit, 'published'),
                        modified   = hitvalue(hit, 'modified'),
                        categories = hitvalue(hit, 'categories'),
                    ))
            #cache.set(KEY, data, TIMEOUT)
        return data
    
    @staticmethod
    def pages_by_category():
        """Returns list of (category, Pages) tuples, alphabetical by category
        
        @returns: list
        """
        KEY = 'encyc-front:pages_by_category'
        TIMEOUT = 60*5
        data = cache.get(KEY)
        if not data:
            categories = {}
            for page in Page.pages():
                for category in page.categories:
                    # exclude internal editorial categories
                    if category not in settings.MEDIAWIKI_HIDDEN_CATEGORIES:
                        if category not in categories.keys():
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
            self.body = unicode(remove_status_markers(BeautifulSoup(self.body)))
    
    def sources(self):
        """Returns list of published light Source objects for this Page.
        
        @returns: list
        """
        return [Source.get(sid) for sid in self.source_ids]
    
    def topics(self):
        """List of DDR topics associated with this page.
        
        @returns: list
        """
        # return list of dicts rather than an Elasticsearch results object
        terms = []
        for t in Elasticsearch.topics_by_url().get(self.absolute_url(), []):
            term = {
                key: val
                for key,val in t.iteritems()
            }
            term.pop('encyc_urls')
            term['ddr_topic_url'] = '%s/%s/' % (
                settings.DDR_TOPICS_BASE,
                term['id']
            )
            terms.append(term)
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
    
    class Meta:
        index = settings.DOCSTORE_INDEX
        doc_type = 'sources'
    
    def __repr__(self):
        return "<Source '%s'>" % self.encyclopedia_id
    
    def __str__(self):
        return self.encyclopedia_id
    
    def absolute_url(self):
        return reverse('rg-source', args=([self.encyclopedia_id]))
    
    def img_url(self):
        return os.path.join(settings.SOURCES_MEDIA_URL, self.img_path)
    
    def img_url_local(self):
        return os.path.join(settings.SOURCES_MEDIA_URL_LOCAL, self.img_path)
    
    #def streaming_url(self):
    #    return os.path.join(settings.SOURCES_MEDIA_URL, self.streaming_path)
    
    def transcript_url(self):
        if self.transcript_path():
            return os.path.join(settings.SOURCES_MEDIA_URL, self.transcript_path())

    @staticmethod
    def dict_list(hit, request):
        data = OrderedDict()
        data['id'] = hit['_source']['encyclopedia_id']
        data['doctype'] = 'sources'
        data['links'] = {}
        data['links']['html'] = api_reverse(
            'rg-source',
            args=([hit['_source']['encyclopedia_id']]),
            request=request,
        )
        data['links']['json'] = api_reverse(
            'rg-api-source', args=([hit['_source']['encyclopedia_id']]),
            request=request,
        )
        return data

    def to_dict_list(self, request=None):
        data = OrderedDict()
        data['id'] = self.encyclopedia_id
        data['doctype'] = 'sources'
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

    def dict_all(self, data=OrderedDict()):
        """Return a dict with all fields
        """
        def setval(self, data, fieldname):
            data[fieldname] = hitvalue(self, fieldname)
        
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
        KEY = 'encyc-front:sources'
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
        return "<Citation '%s'>" % self.url_title
    
    def __str__(self):
        return self.url_title
    
    def __init__(self, page, request):
        self.uri = page.absolute_url()
        self.href = 'http://%s%s' % (request.META['HTTP_HOST'], self.uri)
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
