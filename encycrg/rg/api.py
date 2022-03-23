# -*- coding: utf-8 -*-

from collections import OrderedDict
import json

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response

from django.conf import settings
from django.http import HttpResponsePermanentRedirect

from elastictools import docstore
from . import search as docstore_search
from . import models


def redirect(request):
    return HttpResponsePermanentRedirect(reverse('rg-api-index'))


@api_view(['GET'])
def index(request, format=None):
    data = OrderedDict()
    data['browse'] = reverse('rg-api-browse', request=request)
    data['articles'] = reverse('rg-api-articles', request=request)
    data['authors'] = reverse('rg-api-authors', request=request)
    data['sources'] = reverse('rg-api-sources', request=request)
    data['search'] = reverse('rg-api-search', request=request)
    return Response(data)

@api_view(['GET'])
def articles(request, format=None):
    data = models.Page.pages(
        limit=request.GET.get('limit', settings.PAGE_SIZE),
        offset=request.GET.get('offset', 0),
    ).ordered_dict(
        format_functions=models.FORMATTERS,
        request=request,
        pad=False,
    )
    data.pop('aggregations') # TODO aggregations are not JSON serializable
    return Response(data)

@api_view(['GET'])
def authors(request, format=None):
    data = models.Author.authors(
        limit=request.GET.get('limit', settings.PAGE_SIZE),
        offset=request.GET.get('offset', 0),
    ).ordered_dict(
        format_functions=models.FORMATTERS,
        request=request,
        pad=False,
    )
    data.pop('aggregations') # TODO aggregations are not JSON serializable
    return Response(data)

@api_view(['GET'])
def sources(request, format=None):
    data = models.Source.sources(
        limit=request.GET.get('limit', settings.PAGE_SIZE),
        offset=request.GET.get('offset', 0),
    ).ordered_dict(
        format_functions=models.FORMATTERS,
        request=request,
        pad=False,
    )
    data.pop('aggregations') # TODO aggregations are not JSON serializable
    return Response(data)

@api_view(['GET'])
def article(request, url_title, format=None):
    try:
        article = models.Page.get(url_title)
        article.prepare()
        return Response(
            article.dict_all(request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def author(request, url_title, format=None):
    try:
        return Response(
            models.Author.get(url_title).dict_all(request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def source(request, url_title, format=None):
    try:
        return Response(
            models.Source.get(url_title).dict_all(request)
        )
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)

def _browse(request):
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

@api_view(['GET'])
def browse(request, format=None):
    return Response(
        _browse(request)
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
        limit=request.GET.get('limit', settings.PAGE_SIZE),
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
def search(request, format=None):
    searcher = docstore_search.Searcher(models.DOCSTORE)
    if request.GET.get('fulltext'):
        params = request.GET.copy()
        searcher.prepare(
            params=params,
            params_whitelist=models.PAGE_SEARCH_FIELDS,
            search_models=models.SEARCH_MODELS,
            sort=[],
            fields=models.PAGE_SEARCH_FIELDS,
            fields_nested={},
            fields_agg=models.PAGE_AGG_FIELDS,
        )
    if searcher.params.get('fulltext'):
        limit,offset = docstore_search.limit_offset(request, settings.RESULTS_PER_PAGE)
        data = searcher.execute(limit, offset).ordered_dict(
            request=request,
            format_functions=models.FORMATTERS,
            pad=False,
        )
        # TODO aggregations are not JSON serializable
        data.pop('aggregations')
        return Response(data)
    return Response({})
