""" Import COP Decisions from Informea OData and update Solr index
"""
import requests

from utils import get_date, SolrWrapper


ODATA_COP_DECISIONS_URL = 'http://odata.informea.org/informea.svc/Decisions'
BULK_QUERY = '?$top=%d&$format=json&$orderby=updated desc'
QUERY_FORMAT = '?&$format=json'
LANGUAGES = 'en', 'es', 'fr'

BASE_FIELDS = [
    'id', 'link', 'type', 'status', 'number', 'treaty', 'published', 'updated',
    'meetingId', 'meetingTitle', 'meetingUrl'
]

FIELD_MAP = {
    'id': 'decId',
    'link': 'decLink',

    'title': 'decShortTitle',
    'longTitle': 'decLongTitle',
    'keyword': 'decKeyword',
    'summary': 'decSummary',

    'type': 'decType',
    'status': 'decStatus',
    'number': 'decNumber',
    'treaty': 'decTreatyId',
    'published': 'decPublishDate',
    'updated': 'decUpdateDate',
    'meetingId': 'decMeetingId',
    'meetingTitle': 'decMeetingTitle',
    'meetingUrl': 'decMeetingUrl',
}

solr = SolrWrapper()


def get_url(info):
    if '__deferred' in info:
        return info['__deferred']['uri']


def fetch_document_title(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError('Invalid return code %d' % response.status_code)
    results = response.json()['d']['results']

    titles = {}
    for result in results:
        language = result['language']
        if language not in LANGUAGES:
            continue
        title = result['value']
        titles[language] = title

    return titles


def fetch_document_keywords(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError('Invalid return code %d' % response.status_code)
    results = response.json()['d']['results']

    keywords = {}
    for result in results:
        term = result['term']
        if term not in keywords:
            keywords[term] = True
    return keywords.keys()


def fetch_document_summary(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError('Invalid return code %d' % response.status_code)
    results = response.json()['d']['results']

    summary = None
    # TODO: ASK CRISTI ABOUT SUMMARY FIELD
    return summary


def get_document(base_info):

    document = {'type': 'decision'}

    for field in BASE_FIELDS:
        document[FIELD_MAP[field]] = base_info[field]

    if document['decPublishDate']:
        document['decPublishDate'] = get_date(document['decPublishDate'])
    if document['decUpdateDate']:
        document['decUpdateDate'] = get_date(document['decUpdateDate'])

    title_url = get_url(base_info['title']) + QUERY_FORMAT
    document['decShortTitle'] = fetch_document_title(title_url)

    long_title_url = get_url(base_info['longTitle']) + QUERY_FORMAT
    document['decLongTitle'] = fetch_document_title(long_title_url)

    keywords_url = get_url(base_info['keywords']) + QUERY_FORMAT
    document['decKeyword'] = fetch_document_keywords(keywords_url)

    summary_url = get_url(base_info['summary']) + QUERY_FORMAT
    document['decSummary'] = fetch_document_summary(summary_url)

    decision = solr.search_decision(int(document['decId']))
    if decision:
        # CHECK IF NEEDS UPDATE
        pass
    else:
        # DECISION DOES NOT EXIST! ADD TO SOLR
        print(document['decShortTitle'])
        # solr.add_decision(document)


def fetch_data(limit=10):
    query = BULK_QUERY % (limit, )

    response = requests.get(ODATA_COP_DECISIONS_URL + query)
    if response.status_code != 200:
        raise ValueError('Invalid return code %d' % response.status_code)

    results = response.json()['d']['results']

    # for result in results:
    #     # TODO CHECK IF DOCUMENT NEEDS UPDATED (only then fetch_document)
    #     document = get_document(result)


if __name__ == '__main__':
    fetch_data()
