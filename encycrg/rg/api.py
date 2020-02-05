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
    return Response(models.Page.pages())

@api_view(['GET'])
def authors(request, format=None):
    return Response(models.Author.authors())

@api_view(['GET'])
def sources(request, format=None):
    return Response(models.Source.sources())

@api_view(['GET'])
def article(request, url_title, format=None):
    """DOCUMENTATION GOES HERE.
    """
    try:
        article = models.Page.get(url_title)
        article.prepare()
        return Response(article)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def author(request, url_title, format=None):
    try:
        return Response(models.Author.get(url_title))
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def source(request, url_title, format=None):
    try:
        return Response(models.Source.get(url_title))
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
def browse_field(request, stub, format=None):
    """List databox terms and counts
    """
    return Response(
        models.Page.browse_field(stub, request)
    )

@api_view(['GET'])
def browse_field_value(request, stub, value, format=None):
    """List of articles tagged with databox term.
    """
    results = models.Page.browse_field_objects(stub, value).ordered_dict(
        format_functions=models.FORMATTERS,
        request=request,
        pad=False,
    )
    data['query'] = {}
    data['aggregations'] = {}
    return Response(data)

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

@api_view(['GET'])
def search_form(request, format=None):
    return Response(
        _search(request).ordered_dict(request)
    )


# ----------------------------------------------------------------------

def _browse(request):
    """List of API,UI links and labels for various browse fields
    Use to generate list for browsing
    @returns: list
    """
    fields = []
    for key,val in models.FACET_FIELDS.items():
        stub = val['stub']
        item = OrderedDict()
        item['id'] = key
        item['json'] = reverse('rg-api-browse-field', args=([stub]), request=request)
        item['html'] = reverse('rg-browse-field', args=([stub]), request=request)
        item['title'] = val['label']
        item['description'] = val['description']
        item['icon'] = val['icon']
        item['stub'] = val['stub']
        fields.append(item)
    return fields

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

def _search(request):
    """Search Page objects
    
    @param request: WSGIRequest
    @returns: search.SearchResults
    """
    if hasattr(request, 'query_params'):
        # api (rest_framework)
        params = dict(request.query_params)
    elif hasattr(request, 'GET'):
        # web ui (regular Django)
        params = dict(request.GET)
    else:
        params = {}
        
    # scrub params
    bad_fields = [
        key for key in params.keys()
        if key not in models.PAGE_SEARCH_FIELDS + ['page']
    ]
    for key in bad_fields:
        params.pop(key)
        
    if params.get('page'):
        thispage = int(params.pop('page')[-1])
    else:
        thispage = 0
    limit = settings.DEFAULT_LIMIT
    offset = search.es_offset(limit, thispage)

    s = models.Page.search()
    
    if params.get('fulltext'):
        # MultiMatch chokes on lists
        fulltext = params.pop('fulltext')
        if isinstance(fulltext, list) and (len(fulltext) == 1):
            fulltext = fulltext[0]
        # fulltext search
        s = s.query(
            search.MultiMatch(
                query=fulltext,
                fields=['title', 'body']
            )
        )
        
    # filters
    for key,val in params.items():
        if key in models.PAGE_SEARCH_FIELDS:
            s = s.filter('terms', **{key: val})
    
    # aggregations
    for fieldname in models.PAGE_BROWSABLE_FIELDS.keys():
        s.aggs.bucket(fieldname, 'terms', field=fieldname)
    
    return search.Searcher(
        mappings=MAPPINGS,
        fields=FIELDS,
        search=s,
    ).execute(limit, offset)
