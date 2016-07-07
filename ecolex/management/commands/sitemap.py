import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from ecolex.management.definitions import UNLIMITED_ROWS_COUNT
from ecolex.management.utils import EcolexSolr


class Command(BaseCommand):
    """ Manangement commands that generates the sitemap. """

    def handle(self, *args, **kwargs):
        solr = EcolexSolr()
        docs = solr.search_all('*', fl='slug,type', rows=UNLIMITED_ROWS_COUNT)

        sitemap = os.path.join(settings.STATIC_ROOT, 'sitemap.xml')
        with open(sitemap, 'w') as f:
            f.write(render_to_string('sitemaps/translated_sitemap.xml',
                                     context={'docs': docs}))
