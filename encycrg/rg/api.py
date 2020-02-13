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
def search_form(request, format=None):
    """Search
    
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
