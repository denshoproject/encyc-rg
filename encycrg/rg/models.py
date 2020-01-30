# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from future.utils import python_2_unicode_compatible
from builtins import str
from builtins import object
from collections import OrderedDict
import json
import logging
logger = logging.getLogger(__name__)
import os
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from elasticsearch.exceptions import NotFoundError
import elasticsearch_dsl as dsl

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework.reverse import reverse as api_reverse

from . import repo_models
from . import docstore
from . import search

DOCTYPE_CLASS = {}  # Maps doctype names to classes

SEARCH_LIST_FIELDS = []

"""

from elasticsearch_dsl.connections import connections
from django.conf import settings
from elasticsearch_dsl import Index
from elasticsearch_dsl import DocType, String, Date, Nested, Boolean, analysis
from elasticsearch_dsl import Search
MAX_SIZE = 10000

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
    if isinstance(value, list):
        value = list(value)
    if value and isinstance(value, list) and not is_list:
        value = value[0]
    return value

def _set_attr(obj, hit, fieldname):
    """Assign a SearchResults Hit value if present
    """
    if hasattr(hit, fieldname):
        setattr(obj, fieldname, getattr(hit, fieldname))


AUTHOR_LIST_FIELDS = [
    'url_title',
    'title',
    'title_sort',
    'published',
    'modified',
]

@python_2_unicode_compatible
class Author(repo_models.Author):

    def absolute_url(self):
        return reverse('rg-author', args=([self.title,]))

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return super(Author, Author).get(
            title, index=ds.index_name('author'), using=ds.es
    )

    @staticmethod
    def search():
        """AuthorSearch
        
        @returns: elasticsearch_dsl.Search
        """
        return search.Search().doc_type(Author)
    
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
    def authors(limit=settings.MAX_SIZE, offset=0, num_columns=None):
        """Returns list of published light Author objects.
        
        @returns: list
        """
        KEY = 'encyc-rg:authors:{}:{}'.format(limit, offset)
        data = cache.get(KEY)
        if not data:
            searcher = search.Searcher()
            searcher.prepare(
                params={},
                search_models=[docstore.Docstore().index_name('author')],
                fields_nested=[],
                fields_agg={},
            )
            data = sorted([
                Author.from_hit(hit)
                for hit in searcher.execute(limit, offset).objects
            ])
            if num_columns:
                return _columnizer(data, num_columns)
            cache.set(KEY, data, settings.CACHE_TIMEOUT)
        if num_columns:
            return _columnizer(data, num_columns)
        return data

    @staticmethod
    def from_hit(hit):
        """Creates an Author object from a elasticsearch_dsl.response.hit.Hit.
        """
        obj = Author(
            meta={'id': hit.url_title}
        )
        _set_attr(obj, hit, 'url_title')
        _set_attr(obj, hit, 'public')
        _set_attr(obj, hit, 'published')
        _set_attr(obj, hit, 'modified')
        _set_attr(obj, hit, 'mw_api_url')
        _set_attr(obj, hit, 'title_sort')
        _set_attr(obj, hit, 'title')
        _set_attr(obj, hit, 'body')
        _set_attr(obj, hit, 'article_titles')
        return obj

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
    'description',
    'published',
    'modified',
    'categories',
    'rg_rgmediatype',
    'rg_interestlevel',
    'rg_genre',
    'rg_theme',
    'rg_readinglevel',
    'rg_availability',
]

# fields for browsing
# fields for search aggregations
PAGE_BROWSABLE_FIELDS = {
    'rg_rgmediatype': 'Media Type',
    'rg_interestlevel': 'Interest Level',
    'rg_readinglevel': 'Reading Level',
    'rg_theme': 'Theme',
    'rg_genre': 'Genre',
    'rg_pov': 'Point of View',
    'rg_availability': 'Availability',
    'rg_geography': 'Geography',
    'rg_chronology': 'Chronology',
    'rg_hasteachingaids': 'Has Teaching Aids',
    'rg_freewebversion': 'Free Web Version',
    #'rg_relatedevents': 'Related Events',
    #'rg_denshotopic': 'Topic',
    #'rg_facility': 'Facility',
}

PAGE_SEARCH_FIELDS = [x for x in PAGE_BROWSABLE_FIELDS.keys()]
PAGE_SEARCH_FIELDS.insert(0, 'fulltext')

FACET_FIELDS = OrderedDict()
FACET_FIELDS['rg_rgmediatype'] = {
    'label':'Media Type',
    'description':'The general form of the resource.',
    'icon':'fa-cubes',
    'stub':'media-type',
}
FACET_FIELDS['rg_interestlevel'] = {
    'label':'Interest Level',
    'description':'The grades or ages that would most likely be engaged by the resource.',
    'icon':'fa-graduation-cap',
    'stub':'interest-level',
}
FACET_FIELDS['rg_readinglevel'] = {
    'label':'Reading Level',
    'description':'The general reading level(s) based on grade groupings.',
    'icon':'fa-bookmark',
    'stub':'reading-level',
}
FACET_FIELDS['rg_genre'] = {
    'label':'Genre',
    'description':'The specific category or class of the resource within its media type.',
    'icon':'fa-tags',
    'stub':'genre',
}
FACET_FIELDS['rg_theme'] = {
    'label':'Theme',
    'description':'The universal ideas or messages expressed in the resource.',
    'icon':'fa-compass',
    'stub':'theme',
}
FACET_FIELDS['rg_pov'] = {
    'label':'Point-of-View',
    'description':'The point-of-view and characteristics of the primary protagonist.',
    'icon':'fa-eye',
    'stub':'pov',
}
FACET_FIELDS['rg_geography'] = {
    'label':'Place',
    'description':'The main geographic location(s) depicted in the resource.',
    'icon':'fa-globe',
    'stub':'place',
}
FACET_FIELDS['rg_chronology'] = {
    'label':'Time',
    'description':'The primary time period the resource describes or in which it is set.',
    'icon':'fa-clock-o',
    'stub':'time',
}
FACET_FIELDS['rg_availability'] = {
    'label':'Availabilty',
    'description':'Level of availability, from "Widely available", meaning, "easy to purchase or stream & reasonably priced/free", to "Not available", meaning, "not currently available to purchase or borrow."',
    'icon':'fa-binoculars',
    'stub':'availability',
}
FACET_FIELDS['rg_hasteachingaids'] = {
    'label':'Teaching Aids',
    'description':'The resource includes classroom teaching aids.',
    'icon':'fa-users',
    'stub':'teaching-aids',
}
FACET_FIELDS['rg_freewebversion'] = {
    'label':'Free Web Version',
    'description':'There is a free version available on the web.',
    'icon':'fa-laptop',
    'stub':'free-web-version',
}
MEDIATYPE_URLSTUBS = {val['stub']: key for key,val in FACET_FIELDS.items()}

MEDIATYPE_INFO = {
    'albums': {'label': 'Albums', 'icon': 'fa-music'},
    'articles': {'label': 'Articles', 'icon': 'fa-newspaper-o'},
    'books': {'label': 'Books', 'icon': 'fa-book'},
    'curriculum': {'label': 'Curriculum', 'icon': 'fa-tasks'},
    'essays': {'label': 'Essays', 'icon': 'fa-edit'},
    'exhibitions': {'label': 'Museum Exhibitions', 'icon': 'fa-university'},
    'films': {'label': 'Films and Video', 'icon': 'fa-film'},
    'plays': {'label': 'Plays', 'icon': 'fa-ticket'},
    'short stories': {'label': 'Short Stories', 'icon': 'fa-file-text'},
    'websites': {'label': 'Websites', 'icon': 'fa-laptop'},
}

ACCORDION_SECTIONS = [
    ('moreinfo', 'For_More_Information'),
    ('reviews', 'Reviews'),
    ('footnotes', 'Footnotes'),
    ('related', 'Related_articles'),
]

@python_2_unicode_compatible
class Page(repo_models.Page):
    
    def absolute_url(self):
        return reverse('rg-article', args=([self.title]))
    
    def encyclopedia_url(self):
        return os.path.join(settings.ENCYCLOPEDIA_URL, self.title)

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        page = super(Page, Page).get(
            id=title, index=ds.index_name('article'), using=ds.es
        )
        # only show ResourceGuide items
        if not page.published_rg:
            return None
        page.prepare()
        return page

    def prepare(self):
        soup = BeautifulSoup(self.body, 'html.parser')
        
        # rm databox display tables (note: 'Display' appended to databox name)
        #   <div id="rgdatabox-CoreDisplay">
        for d in [d.split('|')[0] for d in self.databoxes]:
            if soup.find(id='%sDisplay' % d):
                soup.find(id='%sDisplay' % d).decompose()
        
        # rm table of contents div
        #   <div class="toc" id="toc">...
        if soup.find(id='toc'):
            soup.find(id='toc').decompose()
        
        # rm internal top links
        #   <div class="toplink">...
        for tag in soup.find_all(class_="toplink"):
            tag.decompose()

        # prepend encycfront domain for notrg links
        for a in soup.find_all('a', class_='notrg'):
            a['href'] = urljoin(settings.ENCYCLOPEDIA_URL, a['href'])
        
        # rm underscores from internal links
        for a in soup.find_all('a', class_='rg'):
            a['href'] = a['href'].replace('_', ' ')
        
        # rm sections from soup, to separate blocks of HTML
        #   <div class="section" id="For_More_Information">
        #   <div class="section" id="Reviews">
        #   <div class="section" id="Footnotes">
        #   <div class="section" id="Related_articles">
        for fieldname,sectionid in ACCORDION_SECTIONS:
            if soup.find(id=sectionid):
                tag = soup.find(id=sectionid).extract()
                setattr(self, fieldname, tag.prettify())
        
        self.body = soup.prettify()
    
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
        data['description'] = self.description
        
        def setval(self, data, fieldname, is_list=False):
            data[fieldname] = hitvalue(self, fieldname, is_list)

        setval(self, data, 'rg_rgmediatype', is_list=1)
        if self.rg_rgmediatype and MEDIATYPE_INFO.get(self.rg_rgmediatype[0]):
            data['mediatype_label'] = MEDIATYPE_INFO[self.rg_rgmediatype[0]]['label']
            data['mediatype_icon'] = MEDIATYPE_INFO[self.rg_rgmediatype[0]]['icon']
        setval(self, data, 'rg_interestlevel', is_list=1)
        setval(self, data, 'rg_genre', is_list=1)
        setval(self, data, 'rg_theme', is_list=1)
        setval(self, data, 'rg_readinglevel', is_list=1)
        setval(self, data, 'rg_availability', is_list=1)
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
        setval(self, data, 'description')
        #prev_page
        #next_page
        setval(self, data, 'categories')
        setval(self, data, 'source_ids')
        #public
        #published
        setval(self, data, 'published_encyc')
        setval(self, data, 'published_rg')
        setval(self, data, 'modified')
        #mw_api_url
        setval(self, data, 'coordinates')
        #self, 'authors_data'
        data['databoxes'] = {}
        setval(self, data, 'rg_rgmediatype', is_list=1)
        if MEDIATYPE_INFO.get(self.rg_rgmediatype[0]):
            data['mediatype_label'] = MEDIATYPE_INFO[self.rg_rgmediatype[0]]['label']
            data['mediatype_icon'] = MEDIATYPE_INFO[self.rg_rgmediatype[0]]['icon']
        setval(self, data, 'rg_title')
        setval(self, data, 'rg_creators', is_list=1)
        setval(self, data, 'rg_interestlevel', is_list=1)
        setval(self, data, 'rg_readinglevel', is_list=1)
        setval(self, data, 'rg_theme', is_list=1)
        setval(self, data, 'rg_genre', is_list=1)
        setval(self, data, 'rg_pov', is_list=1)
        #setval(self, data, 'rg_relatedevents', is_list=1)
        setval(self, data, 'rg_availability', is_list=1)
        setval(self, data, 'rg_freewebversion', is_list=1)
        #setval(self, data, 'rg_denshotopic')
        setval(self, data, 'rg_geography', is_list=1)
        #setval(self, data, 'rg_facility')
        setval(self, data, 'rg_chronology', is_list=1)
        setval(self, data, 'rg_hasteachingaids', is_list=1)
        setval(self, data, 'rg_warnings', is_list=1)
        setval(self, data, 'body')
        for fieldname,sectionid in ACCORDION_SECTIONS:
            setval(self, data, fieldname)
        # overwrite
        data['categories'] = [
            {
                'json': api_reverse('rg-api-category', args=([category]), request=request),
                'html': api_reverse('rg-category', args=([category]), request=request),
                'title': category,
            }
            for category in self.categories
        ]
        for text in getattr(self, 'databoxes', []):
            key,databox_text = text.split('|')
            if key and databox_text:
                data['databoxes'][key] = json.loads(databox_text)
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
        s = s.filter('term', published_rg=True)
        return s
    
    @staticmethod
    def pages(only_rg=True, limit=settings.MAX_SIZE, offset=0):
        """Returns list of published light Page objects.
        
        @param only_rg: boolean Only return RG pages (rg_rgmediatype present)
        @returns: list
        """
        KEY = 'encyc-rg:pages:{}:{}'.format(limit, offset)
        data = cache.get(KEY)
        if not data:
            params={
                # only ResourceGuide items
                'published_rg': True,
            }
            searcher = search.Searcher()
            searcher.prepare(
                params=params,
                search_models=[docstore.Docstore().index_name('article')],
                fields_nested=[],
                fields_agg={},
            )
            data = sorted([
                Page.from_hit(hit)
                for hit in searcher.execute(limit, offset).objects
            ])
            cache.set(KEY, data, settings.CACHE_TIMEOUT)
        return data
    
    @staticmethod
    def from_hit(hit):
        """Creates a Page object from a elasticsearch_dsl.response.hit.Hit.
        """
        obj = Page(
            meta={'id': hit.url_title}
        )
        _set_attr(obj, hit, 'url_title')
        _set_attr(obj, hit, 'public')
        _set_attr(obj, hit, 'published')
        _set_attr(obj, hit, 'published_encyc')
        _set_attr(obj, hit, 'published_rg')
        _set_attr(obj, hit, 'modified')
        _set_attr(obj, hit, 'mw_api_url')
        _set_attr(obj, hit, 'title_sort')
        _set_attr(obj, hit, 'title')
        _set_attr(obj, hit, 'description')
        _set_attr(obj, hit, 'body')
        _set_attr(obj, hit, 'authors_data')
        _set_attr(obj, hit, 'categories')
        _set_attr(obj, hit, 'coordinates')
        _set_attr(obj, hit, 'source_ids')
        return obj

    @staticmethod
    def titles():
        return [
            page.url_title
            for page in Page.pages()
        ]
     
    @staticmethod
    def pages_by_initial():
        """List of Pages grouped by first letter of title
        Returns list of initial letters, list of groups, total number of Pages
        @returns: (initials,groups,total)
        """
        def _initial_char(text):
            for char in text:
                if char.isdigit():
                    return '1'
                elif char.isalpha():
                    return char
            return char
        
        initials = []
        groups = {}
        for n,page in enumerate(Page.pages()):
            initial = _initial_char(page.title_sort)
            initials.append(initial)
            if not groups.get(initial):
                groups[initial] = []
            groups[initial].append(page)
        initials = sorted(set(initials))
        groups = [
            (initial, groups.pop(initial))
            for initial in initials
        ]
        total = n + 1
        return initials,groups,total
    
    @staticmethod
    def pages_by_category():
        """Returns list of (category, Pages) tuples, alphabetical by category
        
        @returns: list
        """
        KEY = u'encyc-rg:pages_by_category'
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
            cache.set(KEY, data, settings.CACHE_TIMEOUT)
        return data

    @staticmethod
    def mediatypes(pages=None):
        KEY = u'encyc-rg:rgmediatypes'
        data = cache.get(KEY)
        if not data:
            if not pages:
                pages = Page.pages()
            mediatypes = []
            for page in pages:
                mediatypes += page.rg_rgmediatype
            data = set(mediatypes)
            cache.set(KEY, data, settings.CACHE_TIMEOUT)
        return data
    
    def mediatype_label(self):
        if self.rg_rgmediatype and MEDIATYPE_INFO.get(self.rg_rgmediatype[0]):
            return MEDIATYPE_INFO[self.rg_rgmediatype[0]]['label']
    
    def mediatype_icon(self):
        if self.rg_rgmediatype and MEDIATYPE_INFO.get(self.rg_rgmediatype[0]):
            return MEDIATYPE_INFO[self.rg_rgmediatype[0]]['icon']

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
class Source(repo_models.Source):
    
    def absolute_url(self):
        return reverse('rg-source', args=([self.encyclopedia_id]))
    
    def img_url(self):
        return os.path.join(settings.MEDIA_URL, self.img_path)
    
    def img_url_local(self):
        return os.path.join(settings.MEDIA_URL_LOCAL, self.img_path)
    
    def encyc_url(self):
        return '/'.join([settings.ENCYCLOPEDIA_URL, 'sources', self.encyclopedia_id])
    
    #def streaming_url(self):
    #    return os.path.join(settings.SOURCES_MEDIA_URL, self.streaming_path)
    
    def transcript_url(self):
        if self.transcript_path():
            return os.path.join(settings.SOURCES_MEDIA_URL, self.transcript_path())

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return super(Source, Source).get(
            title, index=ds.index_name('source'), using=ds.es
        )

    @staticmethod
    def search():
        """Source Search
        
        @returns: elasticsearch_dsl.Search
        """
        return search.Search().doc_type(Source)

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
        data['links'] = OrderedDict()
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
        data['links']['img'] = self.img_url()
        data['links']['encyc'] = self.encyc_url()
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
    def sources(limit=settings.MAX_SIZE, offset=0):
        """Returns list of published light Source objects.
        
        @returns: list
        """
        KEY = u'encyc-rg:sources:{}:{}'.format(limit, offset)
        data = cache.get(KEY)
        if not data:
            searcher = search.Searcher()
            searcher.prepare(
                params={},
                search_models=[docstore.Docstore().index_name('source')],
                fields_nested=[],
                fields_agg={},
            )
            data = sorted([
                Source.from_hit(hit)
                for hit in searcher.execute(limit, offset).objects
            ])
            cache.set(KEY, data, settings.CACHE_TIMEOUT)
        return data
    
    @staticmethod
    def from_hit(hit):
        """Creates a Source object from a elasticsearch_dsl.response.hit.Hit.
        """
        obj = Source(
            meta={'id': hit.encyclopedia_id}
        )
        _set_attr(obj, hit, 'encyclopedia_id')
        _set_attr(obj, hit, 'densho_id')
        _set_attr(obj, hit, 'psms_id')
        _set_attr(obj, hit, 'psms_api')
        _set_attr(obj, hit, 'institution_id')
        _set_attr(obj, hit, 'collection_name')
        _set_attr(obj, hit, 'created')
        _set_attr(obj, hit, 'modified')
        _set_attr(obj, hit, 'published')
        _set_attr(obj, hit, 'creative_commons')
        _set_attr(obj, hit, 'headword')
        _set_attr(obj, hit, 'original')
        _set_attr(obj, hit, 'original_size')
        _set_attr(obj, hit, 'original_url')
        _set_attr(obj, hit, 'original_path')
        _set_attr(obj, hit, 'original_path_abs')
        _set_attr(obj, hit, 'display')
        _set_attr(obj, hit, 'display_size')
        _set_attr(obj, hit, 'display_url')
        _set_attr(obj, hit, 'display_path')
        _set_attr(obj, hit, 'display_path_abs')
        #_set_attr(obj, hit, 'streaming_path')
        #_set_attr(obj, hit, 'rtmp_path')
        _set_attr(obj, hit, 'streaming_url')
        _set_attr(obj, hit, 'external_url')
        _set_attr(obj, hit, 'media_format')
        _set_attr(obj, hit, 'aspect_ratio')
        _set_attr(obj, hit, 'caption')
        _set_attr(obj, hit, 'caption_extended')
        #_set_attr(obj, hit, 'transcript_path')
        _set_attr(obj, hit, 'transcript')
        _set_attr(obj, hit, 'courtesy')
        _set_attr(obj, hit, 'filename')
        _set_attr(obj, hit, 'img_path')
        return obj


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

@python_2_unicode_compatible
class FacetTerm(repo_models.FacetTerm):
    
    @staticmethod
    def terms(request=None, facet_id=None, limit=settings.DEFAULT_LIMIT, offset=0):
        params={}
        if facet_id:
            params['facet_id'] = facet_id
        searcher = search.Searcher()
        searcher.prepare(
            params=params,
            search_models=[docstore.Docstore().index_name('facetterm')],
            fields_nested=[],
            fields_agg={},
        )
        results = searcher.execute(docstore.MAX_SIZE, 0)
        objects = results.objects
        data = sorted([FacetTerm.from_hit(hit) for hit in objects])
        return data
    
    @staticmethod
    def from_hit(hit):
        """Creates a Source object from a elasticsearch_dsl.response.hit.Hit.
        """
        obj = FacetTerm(
            meta={'id': hit.id}
        )
        _set_attr(obj, hit, 'id')
        _set_attr(obj, hit, 'facet')
        _set_attr(obj, hit, 'term_id')
        if obj.id and not obj.facet:
            obj.facet = obj.id.split('-')[0]
            obj.facet_id = obj.facet
        _set_attr(obj, hit, 'links_html')
        _set_attr(obj, hit, 'links_json')
        _set_attr(obj, hit, 'links_children')
        _set_attr(obj, hit, 'title')
        _set_attr(obj, hit, 'description')
        # topics
        _set_attr(obj, hit, 'path')
        _set_attr(obj, hit, 'parent_id')
        _set_attr(obj, hit, 'ancestors')
        _set_attr(obj, hit, 'siblings')
        _set_attr(obj, hit, 'children')
        _set_attr(obj, hit, 'weight')
        _set_attr(obj, hit, 'encyc_urls')
        # facility
        _set_attr(obj, hit, 'type')
        _set_attr(obj, hit, 'elinks')
        _set_attr(obj, hit, 'location_geopoint')
        return obj
    
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
class Facet(repo_models.Facet):
    
    def absolute_url(self):
        return reverse('rg-facet', args=([self.id]))

    @staticmethod
    def facets(limit=settings.DEFAULT_LIMIT, offset=0):
        searcher = search.Searcher()
        searcher.prepare(
            params={},
            search_models=[docstore.Docstore().index_name('facet')],
            fields_nested=[],
            fields_agg={},
        )
        data = sorted([
            Facet.from_hit(hit)
            for hit in searcher.execute(limit, offset).objects
        ])
        return data
    
    @staticmethod
    def from_hit(hit):
        """Creates a Source object from a elasticsearch_dsl.response.hit.Hit.
        """
        obj = Facet(
            meta={'id': hit.id}
        )
        _set_attr(obj, hit, 'id')
        _set_attr(obj, hit, 'links_html')
        _set_attr(obj, hit, 'links_json')
        _set_attr(obj, hit, 'links_children')
        _set_attr(obj, hit, 'title')
        _set_attr(obj, hit, 'description')
        return obj

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
