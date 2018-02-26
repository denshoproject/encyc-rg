# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse, urlunparse

from elasticsearch.exceptions import NotFoundError, TransportError

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse
from django.views import View
from django.views.debug import technical_500_response

from . import api
from . import forms
from . import models
from . import search

MAPPINGS=models.DOCTYPE_CLASS
FIELDS=models.SEARCH_LIST_FIELDS

def load_templates(default):
    logger.info('loading templates')
    mt = {}
    for m in models.Page.mediatypes():
        try:
            mt[m] = get_template('rg/article-%s.html' % m)
        except:
            mt[m] = default
    return mt

DEFAULT_ARTICLE_LIST_TEMPLATE = get_template('rg/article.html')
MEDIATYPE_TEMPLATES = load_templates(DEFAULT_ARTICLE_LIST_TEMPLATE)


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


def _initial_char(text):
    for char in text:
        if char.isdigit():
            return '1'
        elif char.isalpha():
            return char
    return char

def _group_articles_by_initial(articles):
    initials = []
    groups = {}
    for article in articles:
        initial = _initial_char(article['title_sort'])
        initials.append(initial)
        if not groups.get(initial):
            groups[initial] = []
        groups[initial].append(article)
    initials = sorted(set(initials))
    return initials, [
        (initial, groups.pop(initial))
        for initial in initials
    ]

def articles(request):
    results = api._articles(request, limit=settings.MAX_SIZE)
    initials,groups = _group_articles_by_initial(
        results.to_dict()['objects']
    )
    return render(request, 'rg/articles.html', {
        'num_articles': results.total,
        'initials': initials,
        'groups': groups,
        'fields': models.FACET_FIELDS,
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
    article_titles = api._article_titles(request, limit=settings.MAX_SIZE)
    article = None
    try:
        article = api._article(request, url_title)
    except models.NotFoundError as err:
        # Bad title might just be an author link
        if '_' in url_title:
            return HttpResponsePermanentRedirect(
                reverse('rg-article', args=([
                    url_title.replace('_',' ')
                ]))
            )
        if url_title in article_titles:
            return HttpResponsePermanentRedirect(reverse('rg-author', args=([url_title])))
        raise Http404("No article with that title. (%s)" % err)
    # choose only the first source
    source = None
    if article.source_ids:
        try:
            source = models.Source.get(article.source_ids[0])
        except NotFoundError:
            pass
    # some mediatypes have special templates
    t = MEDIATYPE_TEMPLATES.get(
        article['rg_rgmediatype'][0],
        DEFAULT_ARTICLE_LIST_TEMPLATE
    )
    context = {
        'article': article.dict_all(request=request),
        'source': source,
        'fields': models.FACET_FIELDS,
        'api_url': _mkurl(request, reverse('rg-api-article', args=([url_title]))),
    }
    return HttpResponse(t.render(context, request))


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
    return render(request, 'rg/categories.html', {
        'categories': api._categories(request),
        'api_url': api_url,
    })

def category(request, url_title):
    api_url = _mkurl(request, reverse('rg-api-category', args=([url_title])))
    return render(request, 'rg/category.html', {
        'url_title': url_title,
        'results': api._category(request, category=url_title, limit=settings.MAX_SIZE),
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
        'field_icon': models.FACET_FIELDS[fieldname]['icon'],
        'field_title': models.FACET_FIELDS[fieldname]['label'],
        'field_description': models.FACET_FIELDS[fieldname]['description'],
        'query': r.data,
        'api_url': api_url,
    })

def browse_field_value(request, fieldname, value):
    api_url = _mkurl(request, reverse('rg-api-browse-fieldvalue', args=([fieldname, value])))
    context = {
        'api_url': api_url,
        'fieldname': fieldname,
        'value': value,
        'field_icon': models.FACET_FIELDS[fieldname]['icon'],
        'field_title': models.FACET_FIELDS[fieldname]['label'],
        'field_description': models.FACET_FIELDS[fieldname]['description'],
    }
    if fieldname == 'rg_rgmediatype':
        context['value'] = models.MEDIATYPE_INFO[value]['label']

    results = api._browse_field_value(request, fieldname, value)
    if results.objects:
        paginator = Paginator(
            results.ordered_dict(request=request, pad=True)['objects'],
            results.page_size,
        )
        context['paginator'] = paginator
        context['page'] = paginator.page(results.this_page)
    
    return render(request, 'rg/browse-fieldvalue.html', context)


def search_ui(request):
    api_url = '%s?%s' % (
        _mkurl(request, reverse('rg-api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'api_url': api_url,
        'fields': models.FACET_FIELDS,
    }

    if request.GET.get('fulltext'):

        results = api._search(request)
        form = forms.SearchForm(
            search_results=results,
            data=request.GET
        )
        context['results'] = results
        context['search_form'] = form
        
        if results.objects:
            paginator = Paginator(
                results.ordered_dict(request=request, pad=True)['objects'],
                results.page_size,
            )
            context['paginator'] = paginator
            context['page'] = paginator.page(results.this_page)

    else:
        context['search_form'] = forms.SearchForm()

    # list filters below fulltext field
    filters = [
        (
            models.PAGE_BROWSABLE_FIELDS[key],  # pretty label
            ', '.join(values)
        )
        for key,values in request.GET.lists()
        if key != 'fulltext'
    ]
    context['filters'] = filters
    
    return render(request, 'rg/search.html', context)


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
