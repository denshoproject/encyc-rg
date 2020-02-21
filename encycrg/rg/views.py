# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlunparse

from elasticsearch.exceptions import NotFoundError, TransportError

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.debug import technical_500_response

from . import api
from . import forms
from . import models
from . import search

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
        request.META.get('HTTP_HOST'),
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


@cache_page(settings.CACHE_TIMEOUT)
def articles(request):
    initials,groups,total = models.Page.pages_by_initial()
    return render(request, 'rg/articles.html', {
        'num_articles': total,
        'initials': initials,
        'groups': groups,
        'fields': models.FACET_FIELDS,
        'api_url': _mkurl(request, reverse('rg-api-articles')),
    })

def wiki_article(request, url_title):
    return HttpResponsePermanentRedirect(reverse('rg-article', args=([url_title])))

@cache_page(settings.CACHE_TIMEOUT)
def article(request, url_title):
    article_titles = models.Page.titles()
    article = None
    try:
        article = models.Page.get(url_title)
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


@cache_page(settings.CACHE_TIMEOUT)
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


@cache_page(settings.CACHE_TIMEOUT)
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


@cache_page(settings.CACHE_TIMEOUT)
def browse(request):
    api_url = _mkurl(request, reverse('rg-api-browse'))
    r = api.browse(request, format='json')
    return render(request, 'rg/browse.html', {
        'databox_fields': r.data,
        'api_url': api_url,
    })

@cache_page(settings.CACHE_TIMEOUT)
def browse_field(request, stub):
    if stub not in models.MEDIATYPE_URLSTUBS:
        raise Http404
    # trade the pretty urlstub for the actual mediatype fieldname
    fieldname = models.MEDIATYPE_URLSTUBS[stub]
    if 'rg_' not in fieldname:
        fieldname = 'rg_%s' % fieldname
    api_url = _mkurl(request, reverse('rg-api-browse-field', args=([stub])))
    r = models.Page.browse_field(stub, request)
    return render(request, 'rg/browse-field.html', {
        'stub': stub,
        'fieldname': fieldname,
        'field_icon': models.FACET_FIELDS[fieldname]['icon'],
        'field_title': models.FACET_FIELDS[fieldname]['label'],
        'field_description': models.FACET_FIELDS[fieldname]['description'],
        'query': r,
        'api_url': api_url,
    })

@cache_page(settings.CACHE_TIMEOUT)
def browse_field_value(request, stub, value):
    if stub not in models.MEDIATYPE_URLSTUBS:
        raise Http404
    api_url = _mkurl(request, reverse(
        'rg-api-browse-fieldvalue', args=([stub, value])
    ))
    # trade the pretty urlstub for the actual mediatype fieldname
    fieldname = models.MEDIATYPE_URLSTUBS[stub]
    if fieldname == 'rg_rgmediatype':
        context_value = models.MEDIATYPE_INFO[value]['label']
    else:
        context_value = value
    thispage = int(request.GET.get('page', 1))
    pagesize = settings.RESULTS_PER_PAGE
    offset = models.search_offset(thispage, pagesize)
    results = models.Page.browse_field_objects(stub, value, pagesize, offset)
    paginator = Paginator(
        results.ordered_dict(
            format_functions=models.FORMATTERS,
            request=request,
            pad=True,
        )['objects'],
        results.page_size,
    )
    page = paginator.page(results.this_page)
    return render(request, 'rg/browse-fieldvalue.html', {
        'api_url': api_url,
        'stub': stub,
        'fieldname': fieldname,
        'value': context_value,
        'field_icon': models.FACET_FIELDS[fieldname]['icon'],
        'field_title': models.FACET_FIELDS[fieldname]['label'],
        'field_description': models.FACET_FIELDS[fieldname]['description'],
        'paginator': paginator,
        'page': page,
    })


def search_ui(request):
    api_url = '%s?%s' % (
        _mkurl(request, reverse('rg-api-search')),
        request.META['QUERY_STRING']
    )
    context = {
        'api_url': api_url,
        'fields': models.FACET_FIELDS,
    }

    searcher = search.Searcher()
    if request.GET.get('fulltext'):
        params = request.GET.copy()
        searcher.prepare(
            params=params,
            params_whitelist=models.PAGE_SEARCH_FIELDS,
            search_models=search.SEARCH_MODELS,
            fields=models.PAGE_SEARCH_FIELDS,
            fields_nested={},
            fields_agg=models.PAGE_AGG_FIELDS,
        )
        context['search_performed'] = True
    
    if searcher.params.get('fulltext'):
        limit,offset = search.limit_offset(request)
        results = searcher.execute(limit, offset)
        paginator = Paginator(
            results.ordered_dict(
                request=request,
                format_functions=models.FORMATTERS,
                pad=True,
            )['objects'],
            results.page_size,
        )
        page = paginator.page(results.this_page)
        
        form = forms.SearchForm(
            data=request.GET.copy(),
            search_results=results,
        )
        
        context['results'] = results
        context['paginator'] = paginator
        context['page'] = page
        context['search_form'] = form
        
        # list filters below fulltext field
        filters = [
            (
                models.PAGE_BROWSABLE_FIELDS[key],  # pretty label
                ', '.join(values)
            )
            for key,values in request.GET.lists()
            if (key != 'fulltext') and (key in models.PAGE_BROWSABLE_FIELDS.keys())
        ]
        context['filters'] = filters
        
    else:
        form = forms.SearchForm(
            data=request.GET.copy(),
        )
        context['search_form'] = form

    return render(request, 'rg/search.html', context)
