from django import template
from django.core.urlresolvers import reverse
import datetime

register = template.Library()
INITIAL_DATE = datetime.date(1, 1, 1)


@register.filter
def lookup(d, key):
    return d.get(key, d.get(str(key)))


@register.filter
def just_year(value):
    return value and value[0:4]


@register.filter
def join_by(lst, arg):
    if lst and (type(lst) is list or type(lst) is set):
        return arg.join(lst)
    return lst


@register.filter
def parse_date(d):
    try:
        return datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ').date()
    except:
        return d


@register.filter
def total_seconds(d):
    return (d - INITIAL_DATE).total_seconds() if d else 0


@register.filter
def url_normalize(value):
    return value if value.startswith('http') else 'http://' + value


@register.simple_tag()
def informea_url_id(document):
    # We use this to generate urls to informea.org decisions
    treaty_id = document.solr.get('decTreatyId', None)
    treaty_name = document.solr.get('decTreaty', None)
    if not treaty_id or not treaty_name:
        return ''

    return """<script>
        document.informea_url = "http://www.informea.org/treaties/{url_id}/decision/{dec_id}";
    </script>""".format(url_id=treaty_name, dec_id=document.solr['decId'])


@register.simple_tag()
def breadcrumb(label, viewname='', query='', *args, **kwargs):
    if not viewname:
        return label
    url = reverse(viewname, args=args, kwargs=kwargs)
    if query:
        url = '{url}?{query}'.format(url=url, query=query)
    return '<a href="{url}">{label}</a> &raquo;'.format(url=url, label=label)
