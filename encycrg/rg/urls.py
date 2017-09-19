# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from django.views.generic import TemplateView

from rest_framework.urlpatterns import format_suffix_patterns

from . import api
from . import views

urlpatterns = [
    url(r'^debug/', views.debug, name='rg-debug'),
    
    url(r'^api/1.0/terms/(?P<term_id>[\w\d-]+)/objects/$', api.term_objects, name='rg-api-term-objects'),
    url(r'^api/1.0/terms/(?P<term_id>[\w\d-]+)/$', api.term, name='rg-api-term'),
    url(r'^api/1.0/facets/(?P<facet_id>[\w\d-]+)/terms/$', api.terms, name='rg-api-terms'),
    url(r'^api/1.0/facets/(?P<facet_id>[\w]+)/$', api.facet, name='rg-api-facet'),
    url(r'^api/1.0/facets/$', api.facets, name='rg-api-facets'),

    url(r"^api/1.0/browse/categories/(?P<category>[\w\W]+)/$", api.category, name='rg-api-category'),
    url(r"^api/1.0/browse/categories/$", api.categories, name='rg-api-categories'),
    url(r"^api/1.0/browse/(?P<fieldname>[\w\W]+)/(?P<value>[\w\W]+)/$", api.browse_field_value, name='rg-api-browse-fieldvalue'),
    url(r"^api/1.0/browse/(?P<fieldname>[\w\W]+)/$", api.browse_field, name='rg-api-browse-field'),
    url(r"^api/1.0/browse/$", api.browse, name='rg-api-browse'),
    
    url(r"^api/1.0/articles/(?P<url_title>[\w\W]+)/$", api.article, name='rg-api-article'),
    url(r"^api/1.0/authors/(?P<url_title>[\w\W]+)/$", api.author, name='rg-api-author'),
    url(r"^api/1.0/sources/(?P<url_title>[\w\W]+)/$", api.source, name='rg-api-source'),
    url(r"^api/1.0/articles/$", api.articles, name='rg-api-articles'),
    url(r"^api/1.0/authors/$", api.authors, name='rg-api-authors'),
    url(r"^api/1.0/sources/$", api.sources, name='rg-api-sources'),
    
    url(r'^api/1.0/search/help/$', TemplateView.as_view(template_name="rg/api/search-help.html"), name='rg-api-search-help'),
    url(r"^api/1.0/search/$", api.search_form, name='rg-api-search'),
    
    url(r'^terms/(?P<term_id>[\w\d-]+)/$', views.term, name='rg-term'),
    url(r"^facets/(?P<facet_id>[\w\W]+)/$", views.facet, name='rg-facet'),
    url(r"^facets/$", views.facets, name='rg-facets'),
    
    url(r"^facilities/types/(?P<type_id>[\w\W]+)/$", views.facility_type, name='rg-facility-type'),
    url(r'^facilities/(?P<term_id>[\w\d-]+)/$', views.facility, name='rg-facility'),
    url(r"^facilities/$", views.facilities, name='rg-facilities'),

    url(r'^topics/(?P<term_id>[\w\d-]+)/$', views.topic, name='rg-topic'),
    url(r"^topics/$", views.topics, name='rg-topics'),
    
    url(r"^categories/(?P<url_title>[\w\W]+)/$", views.category, name='rg-category'),
    url(r"^categories/$", views.categories, name='rg-categories'),
    
    url(r"^browse/(?P<fieldname>[\w\W]+)/(?P<value>[\w\W]+)/$", views.browse_field_value, name='rg-browse-fieldvalue'),
    url(r"^browse/(?P<fieldname>[\w\W]+)/$", views.browse_field, name='rg-browse-field'),
    url(r"^browse/$", views.browse, name='rg-browse'),
    
    url(r"^search/$", views.search_ui, name='rg-search'),
    
    #url(r"^wiki/(?P<url_title>[\w\W]+)/$", views.article, name='rg-article'),
    url(r"^wiki/(?P<url_title>[\w\W ,.:\(\)-/]+)/$", views.article, name='rg-article'),
    url(r"^authors/(?P<url_title>[\w\W]+)/$", views.author, name='rg-author'),
    url(r"^sources/(?P<url_title>[\w\W]+)/$", views.source, name='rg-source'),
    
    url(r"^wiki/$", views.articles, name='rg-articles'),
    url(r"^authors/$", views.authors, name='rg-authors'),
    url(r"^sources/$", views.sources, name='rg-sources'),
    
    url(r'^api/1.0/$', api.index, name='rg-api-index'),
    url(r'^$', views.index, name='rg-index'),
]
urlpatterns = format_suffix_patterns(urlpatterns)

handler400 = views.Error400.as_view()
handler403 = views.Error403.as_view()
handler404 = views.Error404.as_view()
handler500 = views.Error500.as_view()
