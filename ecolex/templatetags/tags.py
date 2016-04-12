from django import template
from django.conf import settings
from django.core.urlresolvers import resolve, reverse
from django.utils import translation
from django.utils.html import format_html
from django.template.defaultfilters import capfirst
from django.contrib.staticfiles.finders import get_finders
import datetime
import os
from os.path import basename
from urllib import parse as urlparse

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


@register.filter(name='getattr')
def getattribute(obj, attr):
    return getattr(obj, attr)


@register.filter
def labelify(text):
    return text.replace('_', ' ').capitalize()


@register.filter
def extract_filename(link):
    return basename(urlparse.urlparse(link).path)


@register.filter
def just_year(value):
    return value and value[0:4]


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


@register.simple_tag
def breadcrumb(label, viewname='', query='', *args, **kwargs):
    if not viewname:
        return label
    url = reverse(viewname, args=args, kwargs=kwargs)
    if query:
        url = '{url}?{query}'.format(url=url, query=query)
    return format_html('<a href="{url}">{label}</a> &raquo;',
                       url=url, label=label)


@register.simple_tag(takes_context=True)
def translate_url(context, language):
    view = resolve(context['view'].request.path)
    request_language = translation.get_language()
    translation.activate(language)
    url = reverse(view.url_name, args=view.args, kwargs=view.kwargs)
    translation.activate(request_language)
    return url

@register.filter
def apify_f(data):
    # truncates the facet and returns a {results: [], more: bool} dict
    return {
        'more': len(data) > settings.FACETS_PAGE_SIZE,
        'results': data[:settings.FACETS_PAGE_SIZE],
    }
