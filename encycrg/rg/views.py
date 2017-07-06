# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse, urlunparse

import requests

from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.debug import technical_500_response

from . import models


# views ----------------------------------------------------------------


def index(request):
    api_url = mkurl(request, reverse('rg-api-index'))
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


def mkurl(request, path, query=None):
    return urlunparse((
        request.META['wsgi.url_scheme'],
        request.META['HTTP_HOST'],
        path, None, query, None
    ))
        

def articles(request):
    api_url = mkurl(request, reverse('rg-api-articles'))
    r = requests.get(api_url)
    return render(request, 'rg/articles.html', {
        'articles': json.loads(r.text)['objects'],
        'api_url': api_url,
    })

def article(request, url_title):
    api_url = mkurl(request, reverse('rg-api-article', args=([url_title])))
    r = requests.get(api_url)
    if r.status_code == 404:
        raise Http404("No article with that title.")
    return render(request, 'rg/article.html', {
        'article': json.loads(r.text),
        'api_url': api_url,
    })



def authors(request):
    api_url = mkurl(request, reverse('rg-api-authors'))
    r = requests.get(api_url)
    return render(request, 'rg/authors.html', {
        'authors': json.loads(r.text)['objects'],
        'api_url': api_url,
    })

def author(request, url_title):
    api_url = mkurl(request, reverse('rg-api-author', args=([url_title])))
    r = requests.get(api_url)
    if r.status_code == 404:
        raise Http404("No author with that title.")
    return render(request, 'rg/author.html', {
        'author': json.loads(r.text),
        'api_url': api_url,
    })


def sources(request):
    api_url = mkurl(request, reverse('rg-api-sources'))
    r = requests.get(api_url)
    return render(request, 'rg/sources.html', {
        'sources': json.loads(r.text)['objects'],
        'api_url': api_url,
    })

def source(request, url_title):
    api_url = mkurl(request, reverse('rg-api-source', args=([url_title])))
    r = requests.get(api_url)
    if r.status_code == 404:
        raise Http404("No source with that title.")
    return render(request, 'rg/source.html', {
        'source': json.loads(r.text),
        'api_url': api_url,
    })


def categories(request):
    api_url = mkurl(request, reverse('rg-api-categories'))
    r = requests.get(api_url)
    return render(request, 'rg/categories.html', {
        'categories': json.loads(r.text),
        'api_url': api_url,
    })

def category(request, url_title):
    api_url = mkurl(request, reverse('rg-api-category', args=([url_title])))
    r = requests.get(api_url)
    return render(request, 'rg/category.html', {
        'url_title': url_title,
        'query': json.loads(r.text),
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
    api_url = mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = requests.get(api_url)
    term = json.loads(r.text)
    template = 'rg/term-%s.html' % term['facet_id']
    return render(request, template, {
        'term': term,
        'api_url': api_url,
    })


def topics(request):
    facet_id = 'topics'
    api_url = mkurl(request, reverse('rg-api-terms', args=([facet_id])))
    r = requests.get(api_url)
    return render(request, 'rg/topics.html', {
        'facet_id': facet_id,
        'query': json.loads(r.text),
        'api_url': api_url,
    })

def topic(request, term_id):
    api_url = mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = requests.get(api_url)
    term = json.loads(r.text)
    template = 'rg/term-%s.html' % term['facet_id']
    return render(request, template, {
        'term': term,
        'api_url': api_url,
    })


def browse(request):
    api_url = mkurl(request, reverse('rg-api-browse'))
    r = requests.get(api_url)
    return render(request, 'rg/browse.html', {
        'databox_fields': json.loads(r.text),
        'api_url': api_url,
    })

def browse_field(request, fieldname):
    if 'rg_' not in fieldname:
        fieldname = 'rg_%s' % fieldname
    api_url = mkurl(request, reverse('rg-api-browse-field', args=([fieldname])))
    r = requests.get(api_url)
    return render(request, 'rg/browse-field.html', {
        'fieldname': fieldname,
        'field_title': models.PAGE_BROWSABLE_FIELDS[fieldname],
        'query': json.loads(r.text),
        'api_url': api_url,
    })

def browse_field_value(request, fieldname, value):
    api_url = mkurl(request, reverse('rg-api-browse-fieldvalue', args=([fieldname, value])))
    r = requests.get(api_url)
    return render(request, 'rg/browse-fieldvalue.html', {
        'fieldname': fieldname,
        'field_title': models.PAGE_BROWSABLE_FIELDS[fieldname],
        'value': value,
        'query': json.loads(r.text),
        'api_url': api_url,
    })


def facets(request):
    api_url = mkurl(request, reverse('rg-api-facets'))
    r = requests.get(api_url)
    return render(request, 'rg/facets.html', {
        'facets': json.loads(r.text),
        'api_url': api_url,
    })

def facet(request, facet_id):
    api_url = mkurl(request, reverse('rg-api-terms', args=([facet_id])))
    r = requests.get(api_url)
    return render(request, 'rg/facet.html', {
        'facet_id': facet_id,
        'query': json.loads(r.text),
        'api_url': api_url,
    })

def term(request, term_id):
    api_url = mkurl(request, reverse('rg-api-term', args=([term_id])))
    r = requests.get(api_url)
    term = json.loads(r.text)
    template = 'rg/term-%s.html' % term['facet_id']
    return render(request, template, {
        'term': term,
        'api_url': api_url,
    })
