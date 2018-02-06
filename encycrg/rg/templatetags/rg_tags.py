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
    t = MEDIATYPE_TEMPLATES.get(
        article['rg_rgmediatype'][0],
        DEFAULT_ARTICLE_LIST_TEMPLATE
    )
    c = {
        'article': article,
    }
    return t.render(c)
