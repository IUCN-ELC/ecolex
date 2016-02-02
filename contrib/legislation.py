from utils import EcolexSolr, get_file_from_url


def update_legislation_full_text():
    solr = EcolexSolr()
    doc_number = solr.solr.search('type:legislation').hits
    rows = 100
    index = 0
    while index < doc_number:
        docs = solr.solr.search('type:legislation', start=index, rows=rows)
        new_docs = []
        for doc in docs:
            if 'legLinkToFullText' in doc:
                print(doc['legLinkToFullText'])
                file_obj = get_file_from_url(doc['legLinkToFullText'])
                doc['text'] = solr.extract(file_obj)
                new_docs.append(doc)
        solr.add_bulk(new_docs)
        index += rows
