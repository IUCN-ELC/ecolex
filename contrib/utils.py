from datetime import datetime
import pysolr
import re
import socket
import os


def get_text_tika(file_path):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 1234))
    f = open(file_path, 'rb')

    while True:
        chunk = f.read(65536)
        if not chunk:
            break
        s.sendall(chunk)

    s.shutdown(socket.SHUT_WR)

    file_content = ''
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        file_content += chunk.decode('utf-8')

    return file_content


def get_date(text):
    datestr = re.findall("Date\((.*)\)", text)[0][:-3]
    return datetime.fromtimestamp(int(datestr))


class EcolexSolr(object):
    COP_DECISION = 'COP Decision'
    COURT_DECISION = 'Court Decision'
    TREATY = 'Treaty'

    # This is just an idea, might not be accurate
    ID_MAPPING = {
        COP_DECISION: 'decId',
        COURT_DECISION: 'cdLeoId',
        TREATY: 'trElisId',
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

    def __del__(self):
        self.solr.optimize()
