import json
import pysolr
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

MAX_ROWS = 500


class Command(BaseCommand):
    help = 'Updates the treaties cache'

    def handle(self, *args, **options):
        solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
        result = solr.search('type:treaty AND source:informea,elis',
                             rows=MAX_ROWS)

        data = {
            'response': {
                'numFound': result.hits,
                'docs': result.docs,
            }
        }
        with open(settings.TREATIES_JSON, 'w') as fout:
            json.dump(data, fout)
        self.stdout.write("Done, {} records".format(result.hits))
