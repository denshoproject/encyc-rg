# -*- coding: utf-8 -*-

from django.contrib.sitemaps.views import sitemap
from django.urls import path, re_path
from django.views.generic import TemplateView

from drf_yasg import views as yasg_views
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework.urlpatterns import format_suffix_patterns

from . import api
from . import sitemaps
from . import views

SITEMAPS = {
    'pages': sitemaps.PageSitemap,
}

schema_view = yasg_views.get_schema_view(
   openapi.Info(
      title="Densho Resouce Guide API",
      default_version='3.0',
      description="Densho Resource Guide to Media on the Japanese American Removal and Incarceration",
      terms_of_service="http://resourceguide.densho.org/terms/",
      contact=openapi.Contact(email="info@densho.org"),
      #license=openapi.License(name="TBD"),
   ),
   #validators=['flex', 'ssv'],
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('debug/', views.debug, name='rg-debug'),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='wikiprox-sitemap'),
    
    path('api/swagger.json',
         schema_view.without_ui(cache_timeout=0), name='schema-json'
    ),
    path('api/swagger.yaml',
         schema_view.without_ui(cache_timeout=0), name='schema-yaml'
    ),
    path('api/swagger/',
         schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'
    ),
    path('api/redoc/',
         schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'
    ),
    
    re_path(r'^api/3.0/browse/(?P<stub>[\w\W]+)/(?P<value>[\w\W]+)/', api.browse_facet_objects, name='rg-api-browse-fieldvalue'),
    re_path(r'^api/3.0/browse/(?P<stub>[\w\W]+)/', api.browse_facet, name='rg-api-browse-field'),
    path('api/3.0/browse/', api.browse, name='rg-api-browse'),
    re_path(r'^api/3.0/articles/(?P<url_title>[\w\W]+)/', api.article, name='rg-api-article'),
    re_path(r'^api/3.0/authors/(?P<url_title>[\w\W]+)/', api.author, name='rg-api-author'),
    re_path(r'^api/3.0/sources/(?P<url_title>[\w\W]+)/', api.source, name='rg-api-source'),
    path('api/3.0/articles/', api.articles, name='rg-api-articles'),
    path('api/3.0/authors/', api.authors, name='rg-api-authors'),
    path('api/3.0/sources/', api.sources, name='rg-api-sources'),
    path('api/3.0/search/help/', TemplateView.as_view(template_name="rg/api/search-help.html"), name='rg-api-search-help'),
    path('api/3.0/search/', api.search, name='rg-api-search'),
    path('api/3.0/', api.index, name='rg-api-index'),

    path('api/1.0/', api.redirect, name='rg-api-old-redirect'),
    path('api/', api.redirect, name='rg-api-old-redirect'),
    
    path('browse/title/', views.articles, name='rg-articles'),
    re_path(r'^browse/(?P<stub>[\w\W]+)/(?P<value>[\w\W]+)/', views.browse_field_value, name='rg-browse-fieldvalue'),
    re_path(r'^browse/(?P<stub>[\w\W]+)/', views.browse_field, name='rg-browse-field'),
    path('browse/', views.browse, name='rg-browse'),
    
    path('search/', views.search_ui, name='rg-search'),
    
    re_path(r'^authors/(?P<url_title>[\w\W]+)/', views.author, name='rg-author'),
    re_path(r'^sources/(?P<url_title>[\w\W]+)/', views.source, name='rg-source'),
    
    path('authors/', views.authors, name='rg-authors'),
    path('sources/', views.sources, name='rg-sources'),
    
    path('about/', TemplateView.as_view(template_name="rg/about.html"), name='rg-about'),
    path('terms/', TemplateView.as_view(template_name="rg/terms-of-use.html"), name='rg-terms'),
    
    re_path(r'^wiki/(?P<url_title>[\w\W]+)/', views.wiki_article, name='rg-wiki-article'),
    re_path(r'^(?P<url_title>[\w\W ,.:\(\)-/]+)/', views.article, name='rg-article'),
    
    path('', views.index, name='rg-index'),
]
urlpatterns = format_suffix_patterns(urlpatterns)

handler400 = 'rg.views.handler400'
handler403 = 'rg.views.handler403'
handler404 = 'rg.views.handler404'
handler500 = 'rg.views.handler500'
