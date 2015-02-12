from django import template
from datetime import datetime

register = template.Library()

@register.filter
def lookup(d, key):
    return d.get(key)

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
    return datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ').date()
