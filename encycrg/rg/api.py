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
    return Response(
        fields
    )

@api_view(['GET'])
def browse_facet(request, stub, format=None):
    return Response(
        models.Page.browse_field(stub, request)
    )

@api_view(['GET'])
def browse_facet_objects(request, stub, value, format=None):
    results = models.Page.browse_field_objects(
        stub, value,
        limit=request.GET.get('limit', settings.DEFAULT_LIMIT),
        offset=request.GET.get('offset', 0),
    )
    return Response(
        results.ordered_dict(
            format_functions=models.FORMATTERS,
            request=request,
            pad=False,
        )
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

@api_view(['GET'])
def search_form(request, format=None):
    """
    @param request
    @param format
    @returns: OrderedDict from search.SearchResults
    """
    params = request.GET.copy()
    params['published_rg'] = True  # only ResourceGuide items
    searcher = search.Searcher()
    searcher.prepare(
        params=params,
        params_whitelist=models.PAGE_SEARCH_FIELDS,
        search_models=search.SEARCH_MODELS,
        fields=models.PAGE_SEARCH_FIELDS,
        fields_nested={},
        fields_agg=models.PAGE_AGG_FIELDS,
    )
    limit,offset = search.limit_offset(request)
    data = searcher.execute(limit, offset).ordered_dict(
        request=request,
        format_functions=models.FORMATTERS,
        pad=False,
    )
    # TODO aggregations are not JSON serializable
    data.pop('aggregations')
    return Response(data)


# ----------------------------------------------------------------------

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
