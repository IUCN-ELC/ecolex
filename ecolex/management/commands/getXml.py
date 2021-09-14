import requests
import zipfile
import io

from django.core.management.base import BaseCommand
from django.conf import settings

from ecolex.legislation import harvest_file

class Command(BaseCommand):
    help = 'Get XML and import data'

    def add_arguments(self, parser):
        parser.add_argument('--input_url', type=str, required=True)

    def handle(self, *args, **kwargs):
        input_url = kwargs['input_url']
        resp = requests.get(input_url)
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        z.extractall(settings.BASE_DIR)

        with open("faolex202107.txt", "r") as legislation_file:
            response = harvest_file(legislation_file.read())
            print(response)
