from ecolex.management.utils import EcolexSolr, get_file_from_url


def update_legislation_full_text():
    from ecolex.models import DocumentText
    solr = EcolexSolr()
    doc_number = solr.solr.search('type:legislation').hits
    rows = 100
    index = 0
    while index < doc_number:
        docs = solr.solr.search('type:legislation', start=index, rows=rows)
        new_docs = []
        for doc in docs:
            url = doc.get('legLinkToFullText', None)
            if url:
                if DocumentText.objects.filter(url=url):
                    continue
                file_obj = get_file_from_url(url)
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
