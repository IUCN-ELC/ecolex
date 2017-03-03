from itertools import islice

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from ecolex.settings import DATABASES

from ecolex.models import DocumentText


class Command(BaseCommand):

    help = 'Dump sqlite database using dumpdata. Use a chunked approach to avoid big queries'

    def handle(self, *args, **options):
        if DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Make sure the default database engine is set to sqlite3')

        filen = 0

        # all data except DocumentText
        name = 'sqlite_dump_{0:05d}.json'.format(filen)
        call_command('dumpdata', exclude=['ecolex.DocumentText'], indent=1, output=name)
        filen += 1

        # DocumentText
        step = 1000
        start = 0
        all_pks = DocumentText.objects.values_list('pk', flat=True)
        while start < len(all_pks):
            pks = ','.join(map(str, islice(all_pks, start, start+step)))
            name = 'sqlite_dump_{0:05d}.json'.format(filen)
            call_command('dumpdata', 'ecolex.DocumentText', indent=2, pks=pks, output=name)
            filen += 1
            start += step

