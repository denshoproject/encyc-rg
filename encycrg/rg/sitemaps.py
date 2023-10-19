from datetime import datetime

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from rest_framework.reverse import reverse

from . import models


class Item(object):
    location = ''
    timestamp = None
    
    def unicode(self):
        self.title
    
    def get_absolute_url(self):
        return self.location


class PageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    
    def items(self):
        items = []
        pages = models.Page.pages()
        for hit in pages.objects:
            page = models.Page.from_hit(hit) 
            item = Item()
            item.title = page.title
            item.location = f"/{page.url_title}"
            item.timestamp = page.modified
            items.append(item)
        return items
    
    def lastmod(self, obj):
        return obj.timestamp
