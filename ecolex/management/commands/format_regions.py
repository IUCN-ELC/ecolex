import json
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Format regions XML and store data in JSON'

    def handle(self, *args, **kwargs):
        regions_dict = {}
        with open(settings.SOLR_IMPORT['common']['regions_xml'], "r",
                                            encoding="utf-8") as f_in:
            bs = BeautifulSoup(f_in.read(), 'xml')
            for region in bs.findAll('dictionary_term'):
                countries = region.Region_Countries.string.rsplit('; \n')
                countries[-1] = countries[-1].strip('; ')
                for country in countries:
                    if country not in regions_dict:
                        regions_dict[country] = {
                            'en': [],
                            'fr': [],
                            'es': [],
                        }
                    regions_dict[country]['en'].append(region.Name_en_US.string)
                    regions_dict[country]['fr'].append(region.Name_fr_FR.string)
                    regions_dict[country]['es'].append(region.Name_es_ES.string)

        with open(settings.SOLR_IMPORT['common']['leg_regions_json'], "w",
                                            encoding="utf-8") as f_out:
            json.dump(regions_dict, f_out, indent=2, ensure_ascii=False)
