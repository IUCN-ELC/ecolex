from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = 'Deletes django contenttype objects from database'
    def handle(self, *args, **options):
        resp = ContentType.objects.all().delete()
        print('{} django content types deleted.'.format(resp[0]))
