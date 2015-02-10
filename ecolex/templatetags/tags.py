from django import template

register = template.Library()

@register.filter
def lookup(d, key):
    return d.get(key)

@register.filter
def just_year(value):
    return value and value[0:4]

@register.filter
def join_by(lst, arg):
    if not hasattr(lst, '__iter__'):
        return lst
    return arg.join(lst)
