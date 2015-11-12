from datetime import datetime
from io import BytesIO
import pysolr
import os
import re
import requests


def get_file_from_url(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError('Invalid return code {}'.format(response.status_code))

    doc_content_bytes = response.content
    file_obj = BytesIO()
    file_obj.write(doc_content_bytes)
    setattr(file_obj, 'name', url)
    file_obj.seek(0)
    return file_obj


def get_date(text):
    datestr = re.findall("Date\((.*)\)", text)[0][:-3]
    return datetime.fromtimestamp(int(datestr))


def valid_date(date):
    date_info = date.split('-')
    if len(date_info) != 3:
        return False
    if date_info[0] == '0000' or date_info[1] == '00' or date_info[2] == '00':
        return False
    return True


def format_date(date):
    return date + "T00:00:00Z"


class EcolexSolr(object):
    COP_DECISION = 'COP Decision'
    COURT_DECISION = 'Court Decision'
    TREATY = 'Treaty'
    LITERATURE = 'Literature'

    # This is just an idea, might not be accurate
    ID_MAPPING = {
        COP_DECISION: 'decId',
        COURT_DECISION: 'cdLeoId',
        TREATY: 'trElisId',
        LITERATURE: 'litId',
    }

    def __init__(self):
        solr_uri = os.environ.get('SOLR_URI')
        if not solr_uri:
            raise RuntimeError('SOLR_URI environment variable not set.')
        self.solr = pysolr.Solr(solr_uri, timeout=10)

    def search(self, obj_type, id_value):
        id_field = self.ID_MAPPING.get(obj_type)
        query = '{}:"{}"'.format(id_field, id_value)
        result = self.solr.search(query)
        if result.hits:
            return result.docs[0]

    def add(self, obj):
        self.solr.add([obj])

    def add_bulk(self, bulk_obj):
        self.solr.add(bulk_obj)

    def extract(self, file):
        response = self.solr.extract(file)
        return response['contents']

    def __del__(self):
        self.solr.optimize()
