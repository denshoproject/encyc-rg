# -*- coding: utf-8 -*-
from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

from . import api
from . import views

urlpatterns = [
    url(r'^debug/', views.debug, name='debug'),
    url(r'^api/1.0/$', api.index, name='api-index'),
    url(r'^$', views.Index.as_view(), name='index'),
]
urlpatterns = format_suffix_patterns(urlpatterns)

handler400 = views.Error400.as_view()
handler403 = views.Error403.as_view()
handler404 = views.Error404.as_view()
handler500 = views.Error500.as_view()
