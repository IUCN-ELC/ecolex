import csv
import dicttoxml
import io
import json
import urllib.parse
from datetime import date
from django.core.urlresolvers import reverse
from django.http import HttpResponse


def get_exporter(format):
    exporters = {
        'csv': CSVExporter,
        'json': JsonExporter,
        'xml': XMLExporter,
    }
    return exporters.get(format)


class Exporter(object):
    DATE_FORMAT = '%Y%m%d'

    def __init__(self, docs):
        self.docs = docs

    def attach_urls(self, request):
        export_url = request.build_absolute_uri(reverse('export'))
        qs = {'format': self.FORMAT}
        for doc in self.docs:
            qs['slug'] = doc['slug']
            query = urllib.parse.urlencode(qs)
            doc['export_url'] = '?'.join((export_url, query))

    def get_filename(self):
        current_date = date.today().strftime(self.DATE_FORMAT)
        return 'ecolex_{}'.format(current_date)

    def get_response(self, download=False):
        data = self.get_data()

        resp = HttpResponse(data, content_type=self.CONTENT_TYPE)
        if download:
            filename = self.get_filename()
            content_disposition = 'attachment; filename="{}"'.format(filename)
            resp['Content-Disposition'] = content_disposition

        return resp


class CSVExporter(Exporter):
    CONTENT_TYPE = 'text/csv'
    FORMAT = 'csv'

    def get_data(self):
        if not self.docs:
            return ''

        output = io.StringIO()

        fieldnames = self.docs[0].keys()
        writer = csv.DictWriter(output, fieldnames)

        writer.writeheader()
        for doc in self.docs:
            writer.writerow(doc)

        return output.getvalue()


class JsonExporter(Exporter):
    CONTENT_TYPE = 'application/json'
    FORMAT = 'json'

    def get_data(self):
        return json.dumps(self.docs)


class XMLExporter(Exporter):
    CONTENT_TYPE = 'text/xml'
    FORMAT = 'xml'

    def get_data(self):
        return dicttoxml.dicttoxml(self.docs)
