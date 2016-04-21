from django.core.management.base import BaseCommand
from optparse import make_option

from ecolex.management.utils import EcolexSolr, UNLIMITED_ROWS_COUNT


class Command(BaseCommand):
    """ Management command that checks, for a list field in Solr, if it has more
    than one value for any documents. """

    option_list = BaseCommand.option_list + (
        make_option('--field'),
    )

    def handle(self, *args, **kwargs):
        field = kwargs['field']

        solr = EcolexSolr()
        docs = solr.search_all(field, fl=field, rows=UNLIMITED_ROWS_COUNT)

        if not docs:
            print('No results were found for the specified query.')
            return

        values = [doc[field] for doc in docs]
        lists_longer_than_1 = [v for v in values if len(v) > 1]

        if lists_longer_than_1:
            print('There are {} lists with more than one elements.'
                  .format(len(lists_longer_than_1)))
        else:
            print('This field is probably not a list. {} appearences, all of '
                  'length 1'.format(len(docs)))
