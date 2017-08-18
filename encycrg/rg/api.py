# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from collections import OrderedDict
import json

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from . import models
from . import search

MAPPINGS=models.DOCTYPE_CLASS
FIELDS=models.SEARCH_LIST_FIELDS


@api_view(['GET'])
def index(request, format=None):
    """INDEX DOCS
    """
    data = OrderedDict()
    data['browse'] = reverse('rg-api-browse', request=request)
    data['facets'] = reverse('rg-api-facets', request=request)
    data['articles'] = reverse('rg-api-articles', request=request)
    data['authors'] = reverse('rg-api-authors', request=request)
    data['sources'] = reverse('rg-api-sources', request=request)
    data['search'] = reverse('rg-api-search', request=request)
    return Response(data)

@api_view(['GET'])
def articles(request, format=None):
    return Response(
        _articles(request).ordered_dict(request)
    )

@api_view(['GET'])
def authors(request, format=None):
    return Response(
        _authors(request).ordered_dict(request)
    )

@api_view(['GET'])
def sources(request, format=None):
    return Response(
        _sources(request).ordered_dict(request)
    )

@api_view(['GET'])
def article(request, url_title, format=None):
    """DOCUMENTATION GOES HERE.
    """
    try:
        return Response(
            _article(request, url_title).dict_all(request=request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def author(request, url_title, format=None):
    try:
        return Response(
            _author(request, url_title).dict_all(request=request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def source(request, url_title, format=None):
    try:
        return Response(
            _source(request, url_title).dict_all(request=request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def browse(request, format=None):
    """INDEX DOCS
    """
    return Response(
        _browse(request)
    )

@api_view(['GET'])
def browse_field(request, fieldname, format=None):
    """List databox terms and counts
    """
    return Response(
        _browse_field(request, fieldname)
    )

@api_view(['GET'])
def browse_field_value(request, fieldname, value, format=None):
    """List of articles tagged with databox term.
    """
    return Response(
        _browse_field_value(request, fieldname, value).ordered_dict(request)
    )

@api_view(['GET'])
def categories(request, format=None):
    """CATEGORIES DOCS
    """
    return Response(
        _categories(request)
    )

@api_view(['GET'])
def category(request, category, format=None):
    return Response(
        _category(request, category).ordered_dict(request)
    )

@api_view(['GET'])
def facets(request, format=None):
    return Response(
        _facets(request).ordered_dict(request)
    )

@api_view(['GET'])
def facet(request, facet_id, format=None):
    try:
        return Response(
            _facet(request, facet_id)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def terms(request, facet_id, format=None):
    return Response(
        _terms(request, facet_id).ordered_dict(request)
    )

@api_view(['GET'])
def term(request, term_id, format=None):
    try:
        return Response(
            _term(request, term_id)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def term_objects(request, term_id, limit=settings.DEFAULT_LIMIT, offset=0):
    return Response(
        _term_objects(request, term_id, limit=limit, offset=offset)
    )

class SearchUI(APIView):
    """
    <a href="/api/1.0/search/help/">Search API help</a>
    """
    
    def get(self, request, format=None):
        """
        Search API info and UI.
        """
        return Response({})
    
    def post(self, request, format=None):
        """
        Return search results.
        """
        query = json.loads(request.data['_content'])
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
        offset = int(request.GET.get('offset', 0))
        searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS)
        searcher.prep(query)
        data = searcher.execute(limit, offset).ordered_dict(request)
        return Response(data)


# ----------------------------------------------------------------------

def _articles(request, limit=None, offset=None):
    s = models.Page.search().query("match_all").sort('title_sort')
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    return searcher.execute(limit, offset)

def _article_titles(request, limit=None, offset=None):
    return [
        author.url_title
        for author in _authors(request, limit=limit, offset=offset).objects
    ]

def _authors(request, limit=None, offset=None):
    s = search.Search().doc_type(models.Author).query("match_all")
    s = s.sort('title_sort')
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    return searcher.execute(limit, offset)

def _sources(request, limit=None, offset=None):
    s = search.Search().doc_type(models.Source).query("match_all")
    s = s.sort('encyclopedia_id')
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    return searcher.execute(limit, offset)

def _article(request, url_title):
    return models.Page.get(url_title)

def _author(request, url_title):
    return models.Author.get(url_title)

def _source(request, url_title):
    return models.Source.get(url_title)

def _browse(request):
    data = [
        #{
        #'title': 'categories',
        #'json': reverse('rg-api-categories', request=request),
        #'html': reverse('rg-categories', request=request),
        #},
        #{
        #'title': 'topics',
        #'json': reverse('rg-api-terms', args=(['topics']), request=request),
        #'html': reverse('rg-terms', args=(['topics']), request=request),
        #},
        #{
        #'title': 'facilities',
        #'json': reverse('rg-api-terms', args=(['facility']), request=request),
        #'html': reverse('rg-terms', args=(['facility']), request=request),
        #},
    ]
    for key,val in models.PAGE_BROWSABLE_FIELDS.items():
        data.append({
            'id': key,
            'title': val,
            'json': reverse('rg-api-browse-field', args=([key]), request=request),
            'html': reverse('rg-browse-field', args=([key]), request=request),
        })
    return data

def _browse_field(request, fieldname):
    s = models.Page.search().query("match_all")
    s.aggs.bucket(
        fieldname,
        search.A(
            'terms',
            field=fieldname,
        )
    )
    response = s.execute()
    aggs = search.aggs_dict(response.aggregations.to_dict())[fieldname]
    data = [
        {
            'term': term,
            'count': aggs[term],
            'json': reverse(
                'rg-api-browse-fieldvalue',
                args=([fieldname, term]),
                request=request
            ),
            'html': reverse(
                'rg-browse-fieldvalue',
                args=([fieldname, term]),
                request=request
            ),
        }
        for term in sorted(list(aggs.keys()))
    ]
    return data

def _browse_field_value(request, fieldname, value, limit=None, offset=None):
    s = models.Page.search().from_dict({
        "query": {
            "match": {
                fieldname: value,
            }
        }
    }).sort('title_sort')
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    return searcher.execute(limit, offset)

def _categories(request):
    fieldname = 'categories'
    s = models.Page.search().query("match_all")
    s.aggs.bucket(fieldname, search.A('terms', field=fieldname))
    response = s.execute()
    aggs = search.aggs_dict(response.aggregations.to_dict())[fieldname]
    data = [
        {
            'term': term,
            'count': aggs[term],
            'api_url': reverse(
                'rg-api-browse-fieldvalue',
                args=([fieldname, term]),
                request=request
            ),
            'url': reverse(
                'rg-category',
                args=([term]),
                request=request
            ),
        }
        for term in sorted(list(aggs.keys()))
    ]
    return data

def _category(request, category, limit=None, offset=None):
    """CATEGORY DOCS
    """
    s = models.Page.search().query("match_all")
    s = s.query(
        "match", categories=category
    ).sort('title_sort')
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    return searcher.execute(limit, offset)

def _facets(request, limit=None, offset=None):
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    return search.SearchResults(
        mappings=models.DOCTYPE_CLASS,
        objects=models.Facet.facets(request),
        limit=limit,
        offset=offset,
    )

def _facet(request, facet_id):
    facet = models.Facet.get(facet_id)
    data = facet.dict_all(request)
    data['links']['children'] = reverse(
        'rg-api-terms',
        args=([facet_id]),
        request=request
    )
    return data

def _terms(request, facet_id, limit=None, offset=None):
    if not limit:
        limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    if not offset:
        offset = int(request.GET.get('offset', 0))
    return search.SearchResults(
        mappings=MAPPINGS,
        objects=models.FacetTerm.terms(request, facet_id),
        limit=limit,
        offset=offset,
    )

def _term(request, term_id):
    term = models.FacetTerm.get(term_id)
    data = term.dict_all(request)
    data['links']['children'] = reverse(
        'rg-api-term-objects',
        args=([term_id]),
        request=request
    )
    return data

def _term_objects(request, term_id, limit=settings.DEFAULT_LIMIT, offset=0):
    try:
        term = models.FacetTerm.get(term_id)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = []
    for item in term.encyc_urls:
        d = OrderedDict()
        d['id'] = item['url_title'].replace(u'/', u'').replace(u'%20', u' ')
        d['doctype'] = 'articles'
        d['links'] = {}
        d['links']['json'] = reverse('rg-api-article', args=([item['url_title']]), request=request)
        d['links']['html'] = reverse('rg-article', args=([item['url_title']]), request=request)
        data.append(d)
    return data
