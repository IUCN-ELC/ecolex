import json
import logging
import os
import collections
from django.conf import settings
from django.core.management.base import BaseCommand

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr
from ecolex.management.definitions import TREATY


class Command(BaseCommand):

    """ Updates treaties.json (adds docId based on Solr data)
    """
    def update_json(self):
        with open(settings.TREATIES, encoding="utf-8") as f:
            source_data = json.load(f, object_pairs_hook=collections.OrderedDict)
        ecx_file = os.path.join(settings.CONFIG_DIR, "ecx_tr.json")
        with open(ecx_file, encoding="utf-8") as f:
            ecx_data = json.load(f)
        for rec in ecx_data:
            treaty = next(
                (x for x in source_data.values() if x["uuid"] == rec["trInformeaId"]),
                None
            )
            if not treaty:
                print(f"Treaty not found: {rec['trInformeaId']}")
                continue
            if "docId" in treaty and treaty["docId"] != rec["docId"]:
                print(f"Mismatch for {treaty['uuid']}")
            else:
                treaty["docId"] = rec["docId"]
        with open(settings.TREATIES, "w", encoding="utf-8") as f:
            json.dump(source_data, f, indent=2, ensure_ascii=False)

    """ Updates Solr (adds trInformeaId) based on treaties.json
    """
    def update_solr(self):
        solr = EcolexSolr()
        with open(settings.TREATIES, encoding="utf-8") as f:
            source_data = json.load(f, object_pairs_hook=collections.OrderedDict)
            for treaty in source_data.values():
                uuid = treaty['uuid']
                ecolex_id = treaty.get('docId')
                if ecolex_id:
                    print(f"Checking {ecolex_id}")
                    solr_treaty = solr.search(TREATY, ecolex_id)
                    if 'trInformeaId' not in solr_treaty:
                        # If different uuid, don't update, because treaties.json
                        # might contain several records for the same ecolex_id,
                        # so we just use the first one
                        print(f'Adding {uuid} to {ecolex_id}')
                        update_doc = {
                            'id': solr_treaty['id'],
                            'trInformeaId': uuid,
                        }
                        solr.add(update_doc, fieldUpdates={
                            'trInformeaId': 'set'
                        })
    
    def handle(self, *args, **options):
        self.update_solr()
