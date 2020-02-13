# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from django.views.generic import TemplateView

from rest_framework.urlpatterns import format_suffix_patterns

from . import api
from . import views

urlpatterns = [
    url(r'^debug/', views.debug, name='rg-debug'),

    url(r"^api/1.0/browse/(?P<stub>[\w\W]+)/(?P<value>[\w\W]+)/$", api.browse_facet_objects, name='rg-api-browse-fieldvalue'),
    url(r"^api/1.0/browse/(?P<stub>[\w\W]+)/$", api.browse_facet, name='rg-api-browse-field'),
    url(r"^api/1.0/browse/$", api.browse, name='rg-api-browse'),
    
    url(r"^api/1.0/articles/(?P<url_title>[\w\W]+)/$", api.article, name='rg-api-article'),
    url(r"^api/1.0/authors/(?P<url_title>[\w\W]+)/$", api.author, name='rg-api-author'),
    url(r"^api/1.0/sources/(?P<url_title>[\w\W]+)/$", api.source, name='rg-api-source'),
    url(r"^api/1.0/articles/$", api.articles, name='rg-api-articles'),
    url(r"^api/1.0/authors/$", api.authors, name='rg-api-authors'),
    url(r"^api/1.0/sources/$", api.sources, name='rg-api-sources'),
    
    url(r'^api/1.0/search/help/$', TemplateView.as_view(template_name="rg/api/search-help.html"), name='rg-api-search-help'),
    url(r"^api/1.0/search/$", api.search, name='rg-api-search'),
    
    url(r'^api/1.0/$', api.index, name='rg-api-index'),
    
    url(r"^browse/title/$", views.articles, name='rg-articles'),
    url(r"^browse/(?P<stub>[\w\W]+)/(?P<value>[\w\W]+)/$", views.browse_field_value, name='rg-browse-fieldvalue'),
    url(r"^browse/(?P<stub>[\w\W]+)/$", views.browse_field, name='rg-browse-field'),
    url(r"^browse/$", views.browse, name='rg-browse'),
    
    url(r"^search/$", views.search_ui, name='rg-search'),
    
    url(r"^authors/(?P<url_title>[\w\W]+)/$", views.author, name='rg-author'),
    url(r"^sources/(?P<url_title>[\w\W]+)/$", views.source, name='rg-source'),
    
    url(r"^authors/$", views.authors, name='rg-authors'),
    url(r"^sources/$", views.sources, name='rg-sources'),
    
    url(r'^about/$', TemplateView.as_view(template_name="rg/about.html"), name='rg-about'),
    url(r'^terms/$', TemplateView.as_view(template_name="rg/terms-of-use.html"), name='rg-terms'),
    
    url(r"^wiki/(?P<url_title>[\w\W]+)/$", views.wiki_article, name='rg-wiki-article'),
    url(r"^(?P<url_title>[\w\W ,.:\(\)-/]+)/$", views.article, name='rg-article'),
    
    url(r'^$', views.index, name='rg-index'),
]
urlpatterns = format_suffix_patterns(urlpatterns)

handler400 = views.Error400.as_view()
handler403 = views.Error403.as_view()
handler404 = views.Error404.as_view()
handler500 = views.Error500.as_view()
