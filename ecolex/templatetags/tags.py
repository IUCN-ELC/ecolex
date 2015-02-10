from django import template

register = template.Library()

@register.filter
def lookup(d, key):
    return d.get(key)


@register.filter
def just_year(value):
    return value and value[0:4]
