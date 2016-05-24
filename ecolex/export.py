from datetime import date
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

    def __init__(self, text):
        self.text = text

    def get_data(self):
        return self.text

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


class JsonExporter(Exporter):
    CONTENT_TYPE = 'application/json'


class XMLExporter(Exporter):
    CONTENT_TYPE = 'text/xml'
