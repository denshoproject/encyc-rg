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

@register.inclusion_tag('rg/availabilitylevel-tag.html')
def availabilitylevel(rawlevel):
    """Availability level panel display
    """
    full = ""
    empty = "123"
    leveltext = "No availability (cannot currently be purchased or borrowed)"
    if rawlevel:
        if rawlevel[0].startswith('Limited'):
            full = "1"
            empty = "12"
            leveltext = 'Limited availability (limited for purchase or expensive)'
        elif rawlevel[0].startswith('Available'):
            full = "12"
            empty = "1"
            leveltext = 'Available (moderately easy to obtain)'
        elif rawlevel[0].startswith('Widely'):
            full = "123"
            empty = ""
            leveltext = 'Widely available (easy to purchase or stream and reasonably priced/free)'
    return {'leveltext':leveltext, 'full':full, 'empty':empty}

@register.simple_tag(takes_context=True)
def databox(context):
    """Selects specified databox and displays it in databox-NAME.html template
    
    NOTE: mediatype_label MAY NOT MARCH databox_name!
    """
    DATABOXES = [
            ('books', 'databox-Books'), 
            ('articles', 'databox-Articles'), 
            ('short stories', 'databox-Articles'), 
            ('essays', 'databox-Articles'), 
            ('films', 'databox-Films'), 
            ('plays', 'databox-Plays'), 
            ('exhibitions', 'databox-Exhibitions'), 
            ('websites', 'databox-Websites')
    ]

    databox_id = dict(DATABOXES)[context['article']['rg_rgmediatype'][0]]
    template_name = "rg/{}.html".format(databox_id)
    try:
        t = template.loader.get_template(template_name)
    except:
        t = template.loader.get_template('rg/databox-default.html')
    return t.render({
        'databox': context['article']['databoxes'].get(databox_id, {}),
        'template_name': template_name,
    })
