""" Import COP Decisions from Informea OData and update Solr index
"""
import requests
from datetime import date, timedelta

from utils import get_date


ODATA_URL = "http://odata.informea.org/informea.svc/Decisions"
BULK = "$top=%d&$skip=%d"

FILTER = "$filter=updated gt datetime'%s'"
DUMMY_FILTER = "$filter=type eq 'decision'"
DUMMY_DATE = '2000-01-01T00:00:00'

FORMAT = '$format=json'
EXPAND = '$expand=title,longTitle,keywords,content'
TIMEDELTA = 7  # DAYS

LANGUAGES = ['en', 'es', 'fr']

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

    'content': 'decBody',
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


def fetch_decisions(limit=100):
    # THE CRON WILL RUN WEEKLY, SO WE CHECK THE UPDATES FOR THE LAST WEEK
    today = date.today()
    last_update = today - timedelta(TIMEDELTA)
    date_filter = FILTER % (last_update.strftime("%Y-%m-%dT00:00:00"), )
    date_filter = DUMMY_FILTER  # TESTING PURPOSES UNTIL CRISTI SOLVES BUG

    decisions = []
    skip = 0
    while True and skip < 100:
        bulk = BULK % (limit, skip)

        query = '%s?%s&%s&%s&%s' % (ODATA_URL, bulk, FORMAT, EXPAND,
                                    date_filter)
        response = requests.get(query)
        if response.status_code != 200:
            raise ValueError('Invalid return code %d' % response.status_code)

        results = response.json()['d']['results']
        if not results:
            break
        else:
            decisions.extend(results)
        skip += limit

    return decisions


def parse_multilangual(info):
    titles = {}
    for result in info['results']:
        language = result['language']
        if language not in LANGUAGES:
            continue
        title = result['value']
        titles[language] = title
    return titles or None


def parse_keywords(info):
    keywords = {}
    for result in info['results']:
        term = result['term']
        if term not in keywords:
            keywords[term] = True
    return keywords.keys() or None


def parse_decisions(raw_decisions):
    decisions = []

    for raw_decision in raw_decisions:
        decision = {}

        for field in BASE_FIELDS:
            decision[FIELD_MAP[field]] = raw_decision[field]

        if decision['decPublishDate']:
            decision['decPublishDate'] = get_date(decision['decPublishDate'])
        if decision['decUpdateDate']:
            decision['decUpdateDate'] = get_date(decision['decUpdateDate'])

        decision['decShortTitle'] = parse_multilangual(raw_decision['title'])
        decision['decLongTitle'] = parse_multilangual(raw_decision['longTitle'])
        decision['decKeyword'] = parse_keywords(raw_decision['keywords'])
        decision['decBody'] = parse_multilangual(raw_decision['content'])
        print(decision['decShortTitle'])
        print(decision['decKeyword'])
        print(decision['decBody'])
        print('*****')

    return decisions


if __name__ == '__main__':
    raw_decisions = fetch_decisions()
    decisions = parse_decisions(raw_decisions)
