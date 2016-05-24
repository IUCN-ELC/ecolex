import requests
from urllib.parse import urlencode

MAXCNT = 99999


class RawSolr(object):
    def __init__(self, url):
        self.url = url
        self.handler = 'select'

    def _get_full_url(self, **kwargs):
        base_url = '/'.join([self.url.rstrip('/'), self.handler])
        return '?'.join([base_url, urlencode(kwargs)])

    def query(self, q, fields, format):
        query_url = self._get_full_url(q=q, fl=fields, wt=format, rows=MAXCNT)
        resp = requests.get(query_url)
        return resp.text
