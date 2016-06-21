import json
import re
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option

SOLR_TYPES_MAP = {
    'text': 'String',
    'string': 'String',
    'tdate': 'Date',
    'long': 'Integer',
    'int': 'Integer',
    'double': 'Float',
    'boolean': 'Boolean',
}

DOCTYPE_PREFIXES = ['cd', 'dec', 'ev', 'leg', 'lit', 'tr']

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def strip_prefix(string, prefix):
    return string[len(prefix):]


def strip_suffix(string, suffix):
    return string[:len(string) - len(suffix)]


def ignored_translation(field_name):
    LANGS = ['fr', 'es', 'ar', 'ru', 'zh']
    for lang in LANGS:
        if field_name.endswith('_{}'.format(lang)):
            return True
    return False


class Command(BaseCommand):
    """ Manangement command that genenates schema fields based on the Solr
    schema """

    option_list = BaseCommand.option_list + (
        make_option('--prefix', choices=DOCTYPE_PREFIXES),
    )

    def handle(self, *args, **kwargs):
        prefix = kwargs['prefix']

        resp = requests.get(settings.SOLR_URI + 'schema')
        data = json.loads(resp.text)
        fields = data['schema']['fields']

        for field in fields:
            solr_field_name = field['name']
            if (not field.get('stored') or
                    not solr_field_name.startswith(prefix) or
                    ignored_translation(solr_field_name)):
                continue

            options = []
            if solr_field_name.endswith('_en'):
                solr_field_name = strip_suffix(solr_field_name, '_en')
                options.append('multilingual=True')
            options.append("load_from='{}'".format(solr_field_name))
            options_text = ', '.join(reversed(options))

            field_name = snake_case(strip_prefix(solr_field_name, prefix))
            field_type = SOLR_TYPES_MAP.get(field['type'], 'Field')

            if field.get('multiValued'):
                template = "{name} = fields.List(fields.{type}(), {options})"
            else:
                template = "{name} = fields.{type}({options})"

            print(template.format(
                name=field_name,
                type=field_type,
                options=options_text,
            ))
