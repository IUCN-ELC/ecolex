from django.core.management.base import BaseCommand
from optparse import make_option
import json
import requests
import xmltodict


class Command(BaseCommand):
    """ Manangement commands that converts an XML file to JSON. """

    option_list = BaseCommand.option_list + (
        make_option('--input-url'),
        make_option('--output-file'),
    )

    def handle(self, *args, **kwargs):
        input_url = kwargs['input_url']
        output_file = kwargs['output_file']

        resp = requests.get(input_url)
        content = xmltodict.parse(resp.content)

        keywords = content['result']['dictionary_term']
        json_kw = {}

        for keyword in keywords:
            json_kw[keyword['Name_en_US']] = {
                'fr': keyword['Name_fr_FR'],
                'es': keyword['Name_es_ES'],
            }
            if 'English_Variants' in keyword:
                json_kw[keyword['English_Variants']] = {
                    'fr': keyword.get('French_Variants', ''),
                    'es': keyword.get('Spanish_Variants', ''),
                }

        with open(output_file, 'w') as f:
            json.dump(json_kw, f, indent=2)
