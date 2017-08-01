from django import template
register = template.Library()

@register.simple_tag
def article(article):
    """Page dict
    """
    t = template.loader.get_template('rg/article-list.html')
    c = template.Context({
        'article': article,
    })
    return t.render(c).strip()
