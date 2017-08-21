import os

from bs4 import BeautifulSoup

from django.conf import settings


BASE = '/wiki/'

def url_title(url):
    """Extract url_title from wiki link
    """
    if url[-1] == '/':
        url = url[:-1]
    return url.replace(BASE, '')

def mark(tag, attr, value):
    """Mark tag with specified attr
    """
    if not tag.get(attr):
        tag[attr] = []
    tag[attr].append(value)

def mkoffsite(tag, url_title, encyc_base=settings.ENCYCLOPEDIA_URL):
    """Rewrite tag URL as encycfront URL
    """
    tag['href'] = os.path.join(encyc_base, url_title)

def mark_links(html, article_titles=[], encyc_base=settings.ENCYCLOPEDIA_URL):
    """Add class markers to internal, encyc, offsite links
    """
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all("a"):
        # page nav
        if a['href'][0] == '#':
            pass
        
        # offsite
        elif ('http:' in a['href']) or ('https:' in a['href']):
            mark(a, 'class', 'offsite')
        
        # wiki
        elif (a['href'].find(BASE) == 0):
            urltitle = url_title(a['href'])
            
            # encycrg (this site)
            if urltitle in article_titles:
                mark(a, 'class', 'this')
            
            # encycfront
            else:
                mark(a, 'class', 'encyc')
                mkoffsite(a, urltitle)
    
    return str(soup)
