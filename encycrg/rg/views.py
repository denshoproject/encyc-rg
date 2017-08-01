# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.debug import technical_500_response

from . import api
from . import forms
from . import models
from . import search

MAPPINGS=models.DOCTYPE_CLASS
FIELDS=models.SEARCH_LIST_FIELDS


def _mkurl(request, path, query=None):
    return urlunparse((
        request.META['wsgi.url_scheme'],
        request.META['HTTP_HOST'],
        path, None, query, None
    ))


# views ----------------------------------------------------------------

def index(request):
    api_url = _mkurl(request, reverse('rg-api-index'))
    return render(request, 'rg/index.html', {
        'api_url': api_url,
    })

class Error400(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/400.html', {})

class Error403(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/403.html', {})

class Error404(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/404.html', {})

class Error500(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/500.html', {})

DEBUG_TEXT = """
Scroll down to view request metadata and application settings.
"""

class Debug(Exception):
    pass

def debug(request):
    return technical_500_response(request, Debug, Debug(DEBUG_TEXT), None)

        
def articles(request):
    return render(request, 'rg/articles.html', {
        'results': api._articles(request, limit=settings.MAX_SIZE),
        'api_url': _mkurl(request, reverse('rg-api-articles')),
    })
    #api_url = _mkurl(request, reverse('rg-api-articles'))
    #r = api.get_articles(request)
    #paginator = Paginator(
    #    r.ordered_dict(request=request, pad=True)['objects'],
    #    r.page_size
    #)
    #page = paginator.page(r.this_page)
    #return render(request, 'rg/articles.html', {
    #    'paginator': paginator,
    #    'page': page,
    #    'api_url': api_url,
    #})

def article(request, url_title):
    try:
        article = api._article(request, url_title)
    except models.NotFoundError:
        raise Http404("No article with that title.")
    return render(request, 'rg/article.html', {
        'article': article,
        'api_url': _mkurl(request, reverse('rg-api-article', args=([url_title]))),
    })


def authors(request):
    return render(request, 'rg/authors.html', {
        'results': api._authors(request, limit=settings.MAX_SIZE),
        'api_url': _mkurl(request, reverse('rg-api-authors')),
    })

def author(request, url_title):
    try:
        author = api._author(request, url_title)
    except models.NotFoundError:
        raise Http404("No author with that title.")
    return render(request, 'rg/author.html', {
        'author': author,
        'api_url': _mkurl(request, reverse('rg-api-author', args=([url_title]))),
    })


def sources(request):
    return render(request, 'rg/sources.html', {
        'sources': api._sources(request),
        'api_url': _mkurl(request, reverse('rg-api-sources')),
    })

def source(request, url_title):
    api_url = _mkurl(request, reverse('rg-api-source', args=([url_title])))
    r = api.source(request, url_title, format='json')
    if r.status_code == 404:
        raise Http404("No source with that title.")
    return render(request, 'rg/source.html', {
        'source': r.data,
        'api_url': api_url,
    })


def categories(request):
    api_url = _mkurl(request, reverse('rg-api-categories'))
    r = api.categories(request, format='json')
    return render(request, 'rg/categories.html', {
        'categories': r.data,
        'api_url': api_url,
    })

def category(request, url_title):
    api_url = _mkurl(request, reverse('rg-api-category', args=([url_title])))
    r = api.category(request, category=url_title, format='json')
    return render(request, 'rg/category.html', {
        'url_title': url_title,
        'query': r.data,
        'api_url': api_url,
    })


def facilities(request):
    facet_id = 'facility'
    return render(request, 'rg/facilities.html', {
        'facility_types': models.facility_types(),
    })

def facility_type(request, type_id):
    return render(request, 'rg/facility-type.html', {
        'terms': models.facility_type(type_id),
        'type_id': type_id,
    })

def facility(request, term_id):
    api_url = _mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = api.term(request, term_id, format='json')
    template = 'rg/term-%s.html' % r.data['facet_id']
    return render(request, template, {
        'term': r.data,
        'api_url': api_url,
    })


def topics(request):
    facet_id = 'topics'
    api_url = _mkurl(request, reverse('rg-api-terms', args=([facet_id])))
    r = api.terms(request, facet_id, format='json')
    return render(request, 'rg/topics.html', {
        'facet_id': facet_id,
        'query': r.data,
        'api_url': api_url,
    })

def topic(request, term_id):
    api_url = _mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = api.term(request, term_id, format='json')
    template = 'rg/term-%s.html' % r.data['facet_id']
    return render(request, template, {
        'term': r.data,
        'api_url': api_url,
    })


def browse(request):
    api_url = _mkurl(request, reverse('rg-api-browse'))
    r = api.browse(request, format='json')
    return render(request, 'rg/browse.html', {
        'databox_fields': r.data,
        'api_url': api_url,
    })

def browse_field(request, fieldname):
    if 'rg_' not in fieldname:
        fieldname = 'rg_%s' % fieldname
    api_url = _mkurl(request, reverse('rg-api-browse-field', args=([fieldname])))
    r = api.browse_field(request, fieldname, format='json')
    return render(request, 'rg/browse-field.html', {
        'fieldname': fieldname,
        'field_title': models.PAGE_BROWSABLE_FIELDS[fieldname],
        'query': r.data,
        'api_url': api_url,
    })

def browse_field_value(request, fieldname, value):
    api_url = _mkurl(request, reverse('rg-api-browse-fieldvalue', args=([fieldname, value])))
    r = api.browse_field_value(request, fieldname, value, format='json')
    return render(request, 'rg/browse-fieldvalue.html', {
        'fieldname': fieldname,
        'field_title': models.PAGE_BROWSABLE_FIELDS[fieldname],
        'value': value,
        'query': r.data,
        'api_url': api_url,
    })


def facets(request):
    api_url = _mkurl(request, reverse('rg-api-facets'))
    r = api.facets(request, format='json')
    return render(request, 'rg/facets.html', {
        'facets': r.data,
        'api_url': api_url,
    })

def facet(request, facet_id):
    api_url = _mkurl(request, reverse('rg-api-terms', args=([facet_id])))
    r = api.facets(request, facet_id, format='json')
    return render(request, 'rg/facet.html', {
        'facet_id': facet_id,
        'query': r.data,
        'api_url': api_url,
    })

def term(request, term_id):
    api_url = _mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = api.term(request, term_id, format='json')
    template = 'rg/term-%s.html' % r.data['facet_id']
    return render(request, template, {
        'term': r.data,
        'api_url': api_url,
    })


def search_ui(request):
    api_url = _mkurl(request, reverse('rg-api-search'))
    form = forms.SearchForm(request.GET)
    thispage = int(request.GET.get('page', 0))
    limit = settings.DEFAULT_LIMIT
    offset = search.es_offset(limit, thispage)
    context = {
        'search_form': form,
        'api_url': api_url,
    }
    
    if form.is_valid() and form.cleaned_data.get('fulltext'):
        s = models.Page.search()
        s = s.query(
            search.MultiMatch(
                query=form.cleaned_data.get('fulltext'),
                fields=['title', 'body']
            )
        )
        if form.cleaned_data.get('filter_category'):
            s = s.filter('terms', categories=form.cleaned_data['filter_category'])
        if form.cleaned_data.get('filter_topics'):
            s = s.filter('terms', topics=form.cleaned_data['filter_topics'])
        if form.cleaned_data.get('filter_facility'):
            s = s.filter('terms', facility=form.cleaned_data['filter_facility'])
        
        searcher = search.Searcher(mappings=MAPPINGS, fields=FIELDS, search=s)
        results = searcher.execute(limit, offset)
        if results.objects:
            paginator = Paginator(
                results.ordered_dict(request=request, pad=True)['objects'],
                results.page_size,
            )
            context['paginator'] = paginator
            context['page'] = paginator.page(results.this_page)
    
    return render(request, 'rg/search.html', context)
