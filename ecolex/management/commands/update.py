from django.conf import settings
from django.core.management.base import BaseCommand

from ecolex.management.utils import EcolexSolr, UNLIMITED_ROWS_COUNT


class Command(BaseCommand):
    """ Management command for manual updates in Solr """

    def handle(self, *args, **kwargs):
        if not hasattr(settings, 'SOLR_UPDATE'):
            print('SOLR_UPDATE variable not defined. Please use instructions '
                  'from local_settings.example to configure this variable.')
            return

        replace_from = settings.SOLR_UPDATE['replace']['from']
        replace_to = settings.SOLR_UPDATE['replace']['to']
        replace_field = settings.SOLR_UPDATE['replace']['field']
        filters = settings.SOLR_UPDATE.get('filters', [])

        fq = ' AND '.join(['{field}:"{value}"'.format(**f) for f in filters])
        solr = EcolexSolr()
        docs = solr.search_all(replace_field, '"%s"' % replace_from, fq=fq,
                               rows=UNLIMITED_ROWS_COUNT)

        if not docs:
            print('No docs found matching the query.')
            return

        count = 0
        for doc in docs:
            if isinstance(doc[replace_field], list):
                if replace_from not in doc[replace_field]:
                    continue
                idx = doc[replace_field].index(replace_from)
                doc[replace_field][idx] = replace_to
                count += 1
            else:
                if doc[replace_field] != replace_from:
                    continue
                doc[replace_field] = replace_to
                count += 1

        solr.add_bulk(docs)
        print('{} documents updated.'.format(count))
