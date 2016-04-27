from django.conf import settings
from django.core.management.base import BaseCommand

from ecolex.management.definitions import UNLIMITED_ROWS_COUNT
from ecolex.management.utils import EcolexSolr


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
            replaced_value = doc[replace_field]
            update_doc = {'id': doc['id']}
            if isinstance(replaced_value, list):
                if replace_from not in replaced_value:
                    # This happens in case of an inexact match, i.e. the user
                    # searches for "Ecosystems", but documents containing
                    # "Integrated Ecosystems Management" are also returned
                    continue
                # Remove the replaced value and then add the new value (list)
                update_doc[replace_field] = replace_from
                solr.add(update_doc, fieldUpdates={replace_field: 'remove'})
                update_doc[replace_field] = replace_to
                solr.add(update_doc, fieldUpdates={replace_field: 'add'})
                count += 1
            else:
                if doc[replace_field] != replace_from:
                    continue
                # Just set the new value (non-list)
                update_doc[replace_field] = replace_to
                solr.add(update_doc, fieldUpdates={replace_field: 'set'})
                count += 1

        print('{} documents updated.'.format(count))
