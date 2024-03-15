import json
import os
from bs4 import BeautifulSoup
from functools import lru_cache

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from ecolex.management.commands import format_countries
from ecolex.management.utils import get_dict_from_json

class Command(BaseCommand):
    help = 'Format regions XML and store data in JSON'

    @lru_cache(maxsize=None)
    def find_code_by_name(self, country_name_en):
        for key, names_dict in self.fao_countries.items():
            if names_dict.get("en") == country_name_en:
                return key
        print(f"Cannot find country code for {country_name_en}")
        return None

    def handle(self, *args, **kwargs):
        self.fao_countries = format_countries.Command().load_countries()
        self.ecolex_regions = get_dict_from_json(
            settings.SOLR_IMPORT['common']['regions_json']
        )

        ecolex_replacements = {
            "AFRICA FAO": None,
            "LATIN AMERICA AND THE CARIBBEAN FAO": None,
            "MERCOSUR Countries": None,
            "Andean Community Countries": "Andean States",
        }

        regions_dict = {}
        xml_file = os.path.join(settings.CONFIG_DIR, 'fao_regions.xml')
        with open(xml_file, encoding="utf-8") as f_in:
            bs = BeautifulSoup(f_in.read(), 'xml')
            for region in bs.findAll('dictionary_term'):
                region_name = ecolex_replacements.get(
                    region.Name_en_US.string, region.Name_en_US.string
                )
                if not region_name:
                    # excluded from mapping dict
                    continue

                ecolex_region = self.ecolex_regions.get(region_name.lower())
                if not ecolex_region:
                    print(f"{region_name} not in {settings.SOLR_IMPORT['common']['regions_json']}")
                    continue

                countries = region.Region_Countries.string.split('; \n')
                countries[-1] = countries[-1].strip('; ')
                for country in countries:
                    country_code = self.find_code_by_name(country)
                    if not country_code:
                        continue
                    if country_code not in regions_dict:
                        regions_dict[country_code] = {
                            'en': [],
                            'fr': [],
                            'es': [],
                        }
                    for lang in ("en", "fr", "es"):
                        regions_dict[country_code][lang].append(
                            ecolex_region[lang]
                        )

        with open(settings.SOLR_IMPORT['common']['fao_regions_json'], "w", encoding="utf-8") as f_out:
            json.dump(
                dict(sorted(regions_dict.items())),
                f_out,
                indent=2,
                ensure_ascii=False
            )
