from datetime import datetime
import os
import pysolr
import re


def get_date(text):
    datestr = re.findall("Date\((.*)\)", text)[0][:-3]
    return datetime.fromtimestamp(int(datestr))


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
        return response

    def __del__(self):
        self.solr.optimize()
