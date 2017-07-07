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


# ----------------------------------------------------------------------

@api_view(['GET'])
def articles(request, format=None):
    s = models.Page.search().query("match_all").sort('title_sort')
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    data = searcher.execute(limit, offset).ordered_dict(request)
    return Response(data)

@api_view(['GET'])
def authors(request, format=None):
    s = search.Search().doc_type(models.Author).query("match_all")
    s = s.sort('title_sort')
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    data = searcher.execute(limit, offset).ordered_dict(request)
    return Response(data)

@api_view(['GET'])
def sources(request, format=None):
    s = search.Search().doc_type(models.Source).query("match_all")
    s = s.sort('encyclopedia_id')
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    data = searcher.execute(limit, offset).ordered_dict(request)
    return Response(data)


@api_view(['GET'])
def article(request, url_title, format=None):
    """DOCUMENTATION GOES HERE.
    """
    try:
        page = models.Page.get(url_title)
        #page.scrub()
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(page.dict_all(request=request))

@api_view(['GET'])
def author(request, url_title, format=None):
    try:
        author = models.Author.get(url_title)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(author.dict_all(request=request))

@api_view(['GET'])
def source(request, url_title, format=None):
    try:
        source = models.Source.get(url_title)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(source.dict_all(request=request))


# ----------------------------------------------------------------------

@api_view(['GET'])
def browse(request, format=None):
    """INDEX DOCS
    """
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
    return Response(data)

@api_view(['GET'])
def browse_field(request, fieldname, format=None):
    """List databox terms and counts
    """
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
    return Response(data)

@api_view(['GET'])
def browse_field_value(request, fieldname, value, format=None):
    """List of articles tagged with databox term.
    """
    s = models.Page.search().from_dict({
        "query": {
            "match": {
                fieldname: value,
            }
        }
    }).sort('title_sort')
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    data = searcher.execute(limit, offset).ordered_dict(request)
    return Response(data)


# ----------------------------------------------------------------------

@api_view(['GET'])
def categories(request, format=None):
    """CATEGORIES DOCS
    """
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
    return Response(data)

@api_view(['GET'])
def category(request, category, format=None):
    """CATEGORY DOCS
    """
    s = models.Page.search().query("match_all")
    s = s.query(
        "match", categories=category
    ).sort('title_sort')
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
    data = searcher.execute(limit, offset).ordered_dict(request)
    return Response(data)


# ----------------------------------------------------------------------

@api_view(['GET'])
def facets(request, format=None):
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    return Response(
        search.SearchResults(
            mappings=models.DOCTYPE_CLASS,
            objects=models.Facet.facets(request),
            limit=limit,
            offset=offset,
        ).ordered_dict(request)
    )

@api_view(['GET'])
def facet(request, facet_id, format=None):
    try:
        facet = models.Facet.get(facet_id)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = facet.dict_all(request)
    data['links']['children'] = reverse(
        'rg-api-terms',
        args=([facet_id]),
        request=request
    )
    return Response(data)

@api_view(['GET'])
def terms(request, facet_id, format=None):
    limit = int(request.GET.get('limit', settings.DEFAULT_LIMIT))
    offset = int(request.GET.get('offset', 0))
    return Response(
        search.SearchResults(
            mappings=MAPPINGS,
            objects=models.FacetTerm.terms(request, facet_id),
            limit=limit,
            offset=offset,
        ).ordered_dict(request)
    )

@api_view(['GET'])
def term(request, term_id, format=None):
    try:
        term = models.FacetTerm.get(term_id)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = term.dict_all(request)
    data['links']['children'] = reverse(
        'rg-api-term-objects',
        args=([term_id]),
        request=request
    )
    return Response(data)

@api_view(['GET'])
def term_objects(request, term_id, limit=settings.DEFAULT_LIMIT, offset=0):
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
    return Response(data)


# ----------------------------------------------------------------------

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
