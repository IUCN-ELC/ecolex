from django import template
from datetime import datetime

register = template.Library()


@register.filter
def lookup(d, key):
    return d.get(key, d.get(str(key)))


@register.filter
def just_year(value):
    return value and value[0:4]


@register.filter
def join_by(lst, arg):
    if lst and type(lst) is list:
        return arg.join(lst)
    return lst


@register.filter
def parse_date(d):
    try:
        return datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ').date()
    except:
        return d


@register.simple_tag()
def informea_url_id(document):
    # We use this to generate urls to informea.org decisions.
    treaty_id = document.solr['decTreatyId']
    treaty_name = document.solr['decTreaty']
    if not treaty_id or not treaty_name:
        return ''

    return """<script>
        document.informea_url = "http://www.informea.org/treaties/{url_id}/decision/{dec_id}";
    </script>""".format(url_id=treaty_name, dec_id=document.solr['decId'])
