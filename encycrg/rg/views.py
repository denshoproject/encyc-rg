# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logger = logging.getLogger(__name__)

from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.debug import technical_500_response


# views ----------------------------------------------------------------


class Index(View):
    template = 'rg/index.html'
    def get(self, request, *args, **kwargs):
        return render(request, self.template, {})

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


class articles(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/articles.html', {})

class article(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/article.html', {})


class authors(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/authors.html', {})

class author(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/author.html', {})


class categories(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/categories.html', {})

class category(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/category.html', {})


class sources(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/sources.html', {})

class source(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'rg/source.html', {})
