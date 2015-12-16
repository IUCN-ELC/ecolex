

from utils import EcolexSolr


class TreatyImporter(object):
    def __init__(self, config):
        self.solr_timeout = config.getint('solr_timeout')
        self.treaties_url = config.get('treaties_url')
        self.solr = EcolexSolr(self.solr_timeout)

    def harvest(self):
        pass
