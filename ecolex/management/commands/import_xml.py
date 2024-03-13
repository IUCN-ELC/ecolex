import requests
import zipfile
import io

from django.core.management.base import BaseCommand
from django.conf import settings

from ecolex.legislation import harvest_file

class Command(BaseCommand):
    help = "Get XML and import parsed data"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--input_url", type=str)
        group.add_argument("--filename", type=str)

    def handle(self, *args, **kwargs):
        filename = kwargs["filename"]
        input_url = kwargs["input_url"]
        if not filename:
            resp = requests.get(input_url)
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                z.extractall(settings.BASE_DIR)
                filename = z.namelist()[0]

        with open(filename, "rb") as legislation_file:
            harvest_file(legislation_file.read())
