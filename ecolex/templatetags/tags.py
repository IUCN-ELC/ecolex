from collections import OrderedDict
from django import template
from django.conf import settings
from django.core.urlresolvers import resolve, reverse, Resolver404
from django.utils import translation
from django.utils.html import format_html
from django.utils.translation import ugettext as _
from django.template.defaultfilters import capfirst
from django.contrib.staticfiles.finders import get_finders
import datetime
import json
import re
import os
from html import unescape
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
    filename = basename(urlparse.urlparse(link).path)
    if not filename:
        filename = urlparse.urlparse(link).hostname
    return urlparse.unquote(filename)


@register.filter
def extract_path(link):
    return urlparse.unquote(urlparse.urlparse(link).path)


@register.filter
def extract_hostname(link):
    return urlparse.urlparse(link).hostname


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


@register.filter
def translate_absolute_url(url, language=''):
    repl = '/{}/'.format(language) if language else '/'
    return re.sub(r'(?=\b)\/', repl, url, count=1)


@register.filter
def remove_lang(url):
    return re.sub(r'^(\/fr|\/es)', '', url, count=1)


@register.simple_tag
def breadcrumb(label, viewname='', query='', *args, **kwargs):
    if not viewname:
        return _(label)
    url = reverse(viewname, args=args, kwargs=kwargs)
    if query:
        url = '{url}?{query}'.format(url=url, query=query)
    return format_html('<a href="{url}">{label}</a> &raquo;',
                       url=url, label=_(label))


@register.simple_tag(takes_context=True)
def translate_url(context, language):
    try:
        view = resolve(context['view'].request.path)
    except Resolver404:
        view = resolve('/')
    request_language = translation.get_language()
    translation.activate(language)
    url = reverse(view.url_name, args=view.args, kwargs=view.kwargs)
    translation.activate(request_language)
    return url


@register.filter
def field_urlencoded(field, value):
    return field.form.urlencoded(**{field.name: value})


@register.filter
def get_facet_counts(fdata):
    return {
        f['id']: f['count']
        for f in fdata
    }


@register.filter
def html_unescape(value):
    return unescape(value)


@register.filter
def format_countries(parties):
    event_priority = OrderedDict([
        ('withdrawal', _('Withdrawal')),
        ('entry_into_force', _('Entry into force')),
        ('ratification_group', _('Ratification')),
        ('provisional_application', _('Provisional application')),
        ('simple_signature', _('Simple signature')),
    ])
    with open(settings.PARTY_COUNTRIES) as f:
        codes = json.load(f)
    data = {}
    for party in parties:
        country_code = codes.get(party.country_en, None)
        if not country_code:
            print(party.country_en)
            continue
        main_event = None
        stats = ''
        for event in event_priority.keys():
            party_event = getattr(party, event, {})
            party_event_date = party_event.get('date', None)
            if party_event_date:
                if not main_event:
                    main_event = event_priority[event]
                stats += '<strong>' + event_priority[event] + ': </strong>'
                stats += party_event_date.strftime('%B %d, %Y') + '<br>'

        data[country_code] = {
            'fillKey': main_event,
            'stats': stats,
        }
    return data
