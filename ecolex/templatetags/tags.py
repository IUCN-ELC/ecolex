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


@register.simple_tag(takes_context=True)
def informea_url_id(context, document):
    # We use this to generate urls to informea.org decisions.
    informea_treaty_identifier = {
         1 : "cbd",              # CBD
         2 : "basel",            # Basel Convention
         3 : "cites",            # CITES
         4 : "cms",              # CMS
         5 : "stockholm",        # Stockholm Convention
         6 : "vienna",           # Vienna Convention
         7 : "montreal",         # Montreal Protocol
         8 : "cartagena",        # Cartagena Protocol
         9 : "nagoya",           # Nagoya Protocol
        10 : "aewa",             # AEWA
        14 : "plant-treaty",     # Plant Treaty
        15 : "unfccc",           # UNFCCC
        16 : "whc",              # World Heritage Convention
        17 : "kyoto",            # Kyoto Protocol
        18 : "ramsar",           # Ramsar Convention
        19 : "unccd",            # UNCCD
        20 : "rotterdam",        # Rotterdam Convention
        28 : "gc",               # Governing Council
        43 : "bamako",           # Bamako Convention
        44 : "pollutantrelease", # SEA Protocol
        48 : "unga",             # UNGA
        50 : "ascobans",         # ASCOBANS
        52 : "eurobats",         # EUROBATS
        71 : "unea"              # UNEA
    }
    treaties = context.get('all_treaties')
    if not treaties:
        return ''

    treaty_id = int(treaties[0].solr['trInformeaId'])
    url_id = informea_treaty_identifier.get(treaty_id, None)
    return """<script>
        document.informea_url = "http://www.informea.org/treaties/{url_id}/decision/{dec_id}";
    </script>""".format(url_id=url_id, dec_id=document.solr['decId'])
