# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse, urlunparse

import requests

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.debug import technical_500_response


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
        'category': json.loads(r.text),
        'api_url': api_url,
    })


class facets(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/facets.html', {})

class facet(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/facet.html', {})

class term(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/term.html', {})
