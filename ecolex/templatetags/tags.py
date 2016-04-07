from django import template
from django.core.urlresolvers import resolve, reverse
from django.utils import translation
from django.template.defaultfilters import capfirst
from django.contrib.staticfiles.finders import get_finders
import datetime
import os, re

register = template.Library()
INITIAL_DATE = datetime.date(1, 1, 1)
version_cache = {}

@register.simple_tag
def version(path_string):
    try:
        if path_string in version_cache:
            mtime = version_cache[path_string]
        else:
            for finder in get_finders():
                static_file = finder.find(path_string)
                if static_file:
                    mtime = os.path.getmtime(static_file)
                    version_cache[path_string] = mtime
                    break
        return '%s?%s' % (path_string, mtime,)
    except:
        return path_string

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
def capfirstseq(lst):
    if lst and (type(lst) is list or type(lst) is set):
        return [capfirst(item) for item in lst]
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
    document_type = document.solr.get('type', None)
    if document_type == 'court_decision':
        url = document.solr.get('cdFaoEnglishUrl', None)
        return """<script>
            document.informea_url = "{url}";
            document.hostname = "leo.informea.org";
        </script>""".format(url=url)

    # We use this to generate urls to informea.org decisions
    treaty_id = document.solr.get('decTreatyId', None)
    treaty_name = document.solr.get('decTreaty', None)

    if not treaty_id or not treaty_name:
        return ''

    return """<script>
        document.informea_url = "http://www.informea.org/treaties/{url_id}/decision/{dec_id}";
        document.hostname = "informea.org";
    </script>""".format(url_id=treaty_name, dec_id=document.solr['decId'])


@register.simple_tag()
def faolex_url_id(document):
    return """<script>
        document.faolex_url = "http://faolex.fao.org/cgi-bin/faolex.exe?database=faolex&search_type=query&table=result&query=ID:{leg_id}&format_name=ERALL&lang=eng";
        document.hostname = "faolex.fao.org";
        </script>""".format(leg_id=document.solr.get('legId', 'treaty'))


@register.simple_tag()
def breadcrumb(label, viewname='', query='', *args, **kwargs):
    if not viewname:
        return label
    url = reverse(viewname, args=args, kwargs=kwargs)
    if query:
        url = '{url}?{query}'.format(url=url, query=query)
    return '<a href="{url}">{label}</a> &raquo;'.format(url=url, label=label)


@register.simple_tag(takes_context=True)
def translate_url(context, language):
    view = resolve(context['view'].request.path)
    request_language = translation.get_language()
    translation.activate(language)
    url = reverse(view.url_name, args=view.args, kwargs=view.kwargs)
    translation.activate(request_language)
    return url
