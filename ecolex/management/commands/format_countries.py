import json
import os
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Format countries XML and store data in JSON"

    def load_countries(self):
        countries_dict = {}
        xml_file = os.path.join(settings.CONFIG_DIR, 'fao_countries_ter.xml')
        with open(xml_file, encoding="utf-8") as f_in:
            bs = BeautifulSoup(f_in.read(), "xml")
            for country in bs.findAll("dictionary_term"):
                code = (
                    country.Country_ISO3_Code.string
                    if country.Country_ISO3_Code
                    else country.Country_ISO_Code.string
                )
                countries_dict[code] = {
                    "en": country.Name_en_US.string,
                    "fr": country.Name_fr_FR.string,
                    "es": country.Name_es_ES.string,
                }
        return countries_dict
    
    def handle(self, *args, **kwargs):
        countries_dict = self.load_countries()
        json_file = os.path.join(settings.CONFIG_DIR, 'fao_countries.json')
        with open(json_file, "w", encoding="utf-8") as f_out:
            json.dump(
                dict(sorted(countries_dict.items())),
                f_out,
                indent=2,
                ensure_ascii=False,
            )
