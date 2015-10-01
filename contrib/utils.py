from datetime import datetime
import pysolr
import re
import socket


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


class SolrWrapper(object):

    def __init__(self):
        import os
        solr_uri = os.environ.get('SOLR_URI', '')
        self.solr = pysolr.Solr(solr_uri, timeout=10)

    def search_decision(self, dec_id):
        query = 'decId:"%d"' % (dec_id, )
        results = self.solr.search(query)
        for result in results:
            if result['decId'] == dec_id:
                return result

        return None

    def add_decisions(self, decisions):
        self.solr.add(decisions)
