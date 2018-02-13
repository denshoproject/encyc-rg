import logging
logger = logging.getLogger(__name__)

from django import template
register = template.Library()

from rg import models

def load_templates(default):
    logger.info('loading templates')
    tt = {}
    default = template.loader.get_template('rg/article-list.html')
    for mediatype in models.Page.mediatypes():
        try:
            tt[mediatype] = template.loader.get_template('rg/article-list-%s.html' % mediatype)
        except:
            tt[mediatype] = default
    return tt

DEFAULT_ARTICLE_LIST_TEMPLATE = template.loader.get_template('rg/article-list.html')
MEDIATYPE_TEMPLATES = load_templates(DEFAULT_ARTICLE_LIST_TEMPLATE)

@register.simple_tag
def article(article):
    """Page dict
    """
    mediatype = article.get('rg_rgmediatype', [])
    if mediatype:
        t = MEDIATYPE_TEMPLATES.get(mediatype[0], DEFAULT_ARTICLE_LIST_TEMPLATE)
    else:
        t = DEFAULT_ARTICLE_LIST_TEMPLATE
    c = {
        'article': article,
        'fields': models.FACET_FIELDS,
    }
    return t.render(c)
