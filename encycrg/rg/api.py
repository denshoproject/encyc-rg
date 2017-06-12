# -*- coding: utf-8 -*-

from collections import OrderedDict
import json

from elasticsearch_dsl import Search, A
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from . import models
from . import search


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


# ----------------------------------------------------------------------

@api_view(['GET'])
def articles(request, format=None):
    limit = settings.DEFAULT_LIMIT
    offset = 0
    return Response(
        search.SearchResults(
            objects=models.Page.pages(),
            request=request,
            limit=limit,
            offset=offset,
        ).ordered_dict()
    )

@api_view(['GET'])
def authors(request, format=None):
    limit = settings.DEFAULT_LIMIT
    offset = 0
    return Response(
        search.SearchResults(
            objects=models.Author.authors(),
            request=request,
            limit=limit,
            offset=offset,
        ).ordered_dict()
    )

@api_view(['GET'])
def sources(request, format=None):
    limit = settings.DEFAULT_LIMIT
    offset = 0
    return Response(
        search.SearchResults(
            objects=models.Source.sources(),
            request=request,
            limit=limit,
            offset=offset,
        ).ordered_dict()
    )


@api_view(['GET'])
def article(request, url_title, format=None):
    """DOCUMENTATION GOES HERE.
    """
    try:
        page = models.Page.get(url_title)
        #page.scrub()
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    #topic_term_ids = [
    #    '%s/facet/topics/%s/objects/' % (settings.DDR_API, term['id'])
    #    for term in page.topics()
    #]
    data = OrderedDict()
    # put these at the top because OrderedDict
    data['id'] = url_title
    data['links'] = OrderedDict()
    data['links']['json'] = reverse('rg-api-article', args=([url_title]), request=request)
    data['links']['html'] = reverse('rg-article', args=([url_title]), request=request)
    data['categories'] = []
    data['topics'] = []
    data['authors'] = []
    data['sources'] = []
    # fill in
    data = page.dict_all(data=data)
    # overwrite
    data['categories'] = [
        reverse('rg-api-category', args=([category]), request=request)
        for category in page.categories
    ]
    #'ddr_topic_terms': topic_term_ids,
    data['sources'] = [
        reverse('rg-api-source', args=([source_id]), request=request)
        for source_id in page.source_ids
    ]
    data['authors'] = [
        reverse('rg-api-author', args=([author_titles]), request=request)
        for author_titles in page.authors_data['display']
    ]
    return Response(data)

@api_view(['GET'])
def author(request, url_title, format=None):
    try:
        author = models.Author.get(url_title)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = OrderedDict()
    # put these at the top because OrderedDict
    data['id'] = url_title
    data['links'] = OrderedDict()
    data['links']['json'] = reverse('rg-api-author', args=([url_title]), request=request)
    data['links']['html'] = reverse('rg-author', args=([url_title]), request=request)
    data['articles'] = []
    # fill in
    data = author.dict_all(data=data)
    # overwrite
    data['articles'] = [
        reverse('rg-api-article', args=([page.url_title]), request=request)
        for page in author.articles()
    ]
    return Response(data)

@api_view(['GET'])
def source(request, url_title, format=None):
    try:
        source = models.Source.get(url_title)
    except models.NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data = OrderedDict()
    # put these at the top because OrderedDict
    data['id'] = url_title
    data['links'] = OrderedDict()
    data['links']['json'] = reverse('rg-api-source', args=([url_title]), request=request)
    data['links']['html'] = reverse('rg-source', args=([url_title]), request=request)
    # fill in
    data = source.dict_all(data=data)
    # overwrite
    return Response(data)


# ----------------------------------------------------------------------

@api_view(['GET'])
def browse(request, format=None):
    """INDEX DOCS
    """
    data = OrderedDict()
    data['categories'] = reverse('rg-api-categories', request=request)
    for field in models.PAGE_BROWSABLE_FIELDS:
        label = field.replace('rg_', '')
        data[label] = reverse(
            'rg-api-browse-field', args=([field]), request=request
        )
    return Response(data)

@api_view(['GET'])
def browse_field(request, fieldname, format=None):
    """List databox terms and counts
    """
    s = Search().doc_type(models.Page).query("match_all")
    s.aggs.bucket(
        fieldname,
        A(
            'terms',
            field=fieldname,
        )
    )
    response = s.execute()
    aggs = search.aggs_dict(response.aggregations.to_dict())[fieldname]
    data = [
        {
            'term': term,
            'count': count,
            'url': reverse(
                'rg-api-browse-fieldvalue',
                args=([fieldname, term]),
                request=request
            ),
        }
        for term,count in aggs.iteritems()
    ]
    return Response(data)

@api_view(['GET'])
def browse_field_value(request, fieldname, value, format=None):
    """List of articles tagged with databox term.
    """
    query = {
        "query": {
            "match": {
                fieldname: value,
            }
        }
    }
    limit = settings.DEFAULT_LIMIT
    offset = 0
    return Response(
        search.SearchResults(
            query=query,
            results=Search().doc_type(models.Page).from_dict(query).execute(),
            request=request,
            limit=limit,
            offset=offset,
        ).ordered_dict()
    )


# ----------------------------------------------------------------------

@api_view(['GET'])
def categories(request, format=None):
    """CATEGORIES DOCS
    """
    fieldname = 'categories'
    s = Search().doc_type(models.Page).query("match_all")
    s.aggs.bucket(fieldname, A('terms', field=fieldname))
    response = s.execute()
    aggs = search.aggs_dict(response.aggregations.to_dict())[fieldname]
    data = [
        {
            'term': term,
            'count': count,
            'url': reverse(
                'rg-api-browse-fieldvalue',
                args=([fieldname, term]),
                request=request
            ),
        }
        for term,count in aggs.iteritems()
    ]
    return Response(data)

@api_view(['GET'])
def category(request, category, format=None):
    """CATEGORY DOCS
    """
    query = {
        'doctypes': ['articles'],
        'must': {
            "match": {
                "categories": category,
            }
        }
    }
    limit = DEFAULT_LIMIT
    offset = 0
    return Response(search.run_search(
        request_data=query,
        request=request,
        sort_fields=[],
        limit=limit,
        offset=offset,
    ).ordered_dict())


# ----------------------------------------------------------------------

class SearchUI(APIView):
    """
    <a href="/api/0.2/search/help/">Search API help</a>
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
        limit = settings.DEFAULT_LIMIT
        offset = 0
        return Response(search.run_search(
            request_data=json.loads(request.data['_content']),
            request=request,
            sort_fields=[],
            limit=limit,
            offset=offset,
        ).ordered_dict())
