from datetime import datetime
from io import BytesIO
import json
import pysolr
import os
import re
import requests

TREATY = 'treaty'
COP_DECISION = 'decision'
LEGISLATION = 'legislation'
COURT_DECISION = 'court_decision'
LITERATURE = 'literature'

OBJ_TYPES = [TREATY, COP_DECISION, LEGISLATION, COURT_DECISION, LITERATURE]

DEC_TREATY_FIELDS = ['partyCountry', 'trSubject_en']


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


def get_json_from_url(url, headers={}):
    resp = requests.get(url, headers=headers)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')

    try:
        return json.loads(resp.text)
    except ValueError as ex:
        # TODO: replace this with logging
        print(url, ex)


def get_content_from_url(url):
    resp = requests.get(url)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')
    return resp.content


class EcolexSolr(object):

    # This is just an idea, might not be accurate
    ID_MAPPING = {
        COP_DECISION: 'decId',
        COURT_DECISION: 'cdLeoId',
        TREATY: 'trElisId',
        LITERATURE: 'litId',
    }

    def __init__(self, timeout=10):
        solr_uri = os.environ.get('SOLR_URI')
        if not solr_uri:
            raise RuntimeError('SOLR_URI environment variable not set.')
        self.solr = pysolr.Solr(solr_uri, timeout=timeout)

    def search(self, obj_type, id_value):
        id_field = self.ID_MAPPING.get(obj_type)
        result = self.search_all(id_field, id_value)
        return result[0] if result else None

    def search_all(self, key, value):
        query = '{}:"{}"'.format(key, value)
        result = self.solr.search(query)
        if result.hits:
            return result.docs

    def add(self, obj):
        self.solr.add([obj])
        self.solr.optimize()

    def add_bulk(self, bulk_obj):
        self.solr.add(bulk_obj)
        self.solr.optimize()

    def extract(self, file):
        # TODO should probably catch and log it in the caller
        try:
            response = self.solr.extract(file)
        except pysolr.SolrError:
            return ''
        return response['contents']
