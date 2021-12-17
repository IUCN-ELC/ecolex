import json
import logging
import logging.config
from datetime import datetime

from django.db.utils import OperationalError
from django.conf import settings
from pysolr import SolrError

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import LEGISLATION
from ecolex.management.utils import EcolexSolr, get_file_from_url, cleanup_copyfields

from ecolex.management.utils import get_content_length_from_url
from ecolex.models import DocumentText


logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger("legislation_import")


class LegislationImporter(object):

    def __init__(self, config):
        self.solr_timeout = config.get("solr_timeout")
        self.solr = EcolexSolr(self.solr_timeout)

    def update_full_text(self, obj):
        if not obj:
            return
        # Check if already parsed
        text = None
        if obj.doc_size and obj.text:
            logger.info(f"Checking content length of "
                        f"{obj.doc_id} ({obj.url})")
            doc_size = get_content_length_from_url(obj.url)
            if doc_size == obj.doc_size:
                # File not changed, reuse obj.text
                logger.debug(f"Not changed: {obj.url}")
                text = obj.text

        # Download file
        if not text:
            logger.info(f"Downloading: {obj.doc_id} ({obj.url})")
            file_obj = get_file_from_url(obj.url)
            if not file_obj:
                logger.error(f"Failed downloading: {obj.url}")
                return
            doc_size = file_obj.getbuffer().nbytes

            # Extract text
            logger.debug(f"Indexing: {obj.url}")
            text = self.solr.extract(file_obj)
            if not text:
                logger.warn(f"Nothing to index for {obj.url}")

        # Load record and store text
        try:
            legislation = self.solr.search(LEGISLATION, obj.doc_id)
            if legislation:
                legislation = cleanup_copyfields(legislation)
        except SolrError as e:
            logger.error(f"Error reading legislation {obj.doc_id}")
            if settings.DEBUG:
                logging.getLogger("solr").exception(e)
            return

        if not legislation:
            logger.error(f"Failed to find legislation {obj.doc_id}")
            return

        legislation["legText"] = text
        result = self.solr.add(legislation)
        if result:
            logger.info(f"Success download & indexed: {obj.doc_id}")
            obj.doc_size = doc_size
            obj.text = text
            try:
                obj.save()
            except OperationalError as e:
                logger.error(f"DB insert error {obj.doc_id} {e}")
                obj.text = None
                obj.save()
        else:
            logger.error(f"Failed doc extract {obj.url} {legislation['id']}")

    def reindex_failed(self, obj):
        legislation = json.loads(obj.parsed_data)
        legislation["updatedDate"] = (datetime.now()
                                      .strftime("%Y-%m-%dT%H:%M:%SZ"))
        # Check if already present in Solr
        if "id" not in legislation:
            try:
                old_legislation = self.solr.search(LEGISLATION, obj.doc_id)
                if old_legislation:
                    legislation["id"] = old_legislation["id"]
                    legislation = cleanup_copyfields(legislation)
            except SolrError as e:
                logger.error(f"Error reading legislation {obj.doc_id}")
                if settings.DEBUG:
                    logging.getLogger("solr").exception(e)
                return
        result = self.solr.add(legislation)
        if result:
            obj.parsed_data = ""
            obj.save()
            logger.info(f"Success indexing: {obj.doc_id}")
        else:
            logger.error(f"Failed to index: {obj.doc_id}")
