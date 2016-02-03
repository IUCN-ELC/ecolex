import os
import sys

project_path = "/ecolex/"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecolex.settings")
sys.path.append(project_path)
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from utils import EcolexSolr, get_file_from_url
from ecolex.models import DocumentText


def update_legislation_full_text():
    solr = EcolexSolr()
    doc_number = solr.solr.search('type:legislation').hits
    rows = 100
    index = 0
    while index < doc_number:
        docs = solr.solr.search('type:legislation', start=index, rows=rows)
        new_docs = []
        for doc in docs:
            if DocumentText.objects.filter(doc_id=doc['id']):
                continue
            if 'legLinkToFullText' in doc:
                print(doc['legLinkToFullText'])
                file_obj = get_file_from_url(doc['legLinkToFullText'])
                doc_size = file_obj.getbuffer().nbytes
                doc['text'] = solr.extract(file_obj)
                new_docs.append(doc)
                document_text = DocumentText(doc_id=doc['id'],
                                             url=doc['legLinkToFullText'],
                                             text=doc['text'],
                                             doc_size=doc_size)
                document_text.save()
        solr.add_bulk(new_docs)
        index += rows
