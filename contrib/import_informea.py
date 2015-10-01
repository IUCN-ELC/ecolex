""" Import COP Decisions from Informea OData and update Solr index
"""
import re
import requests
from datetime import date, timedelta

from utils import get_date, SolrWrapper


ODATA_URL = "http://odata.informea.org/informea.svc/Decisions"
BULK = "$top=%d&$skip=%d"

FILTER = "$filter=updated gt datetime'%s'"
DUMMY_FILTER = "$filter=type eq 'decision'"
DUMMY_DATE = '2000-01-01T00:00:00'

FORMAT = '$format=json'
EXPAND = '$expand=title,longTitle,keywords,content'
TIMEDELTA = 7  # DAYS

LANGUAGES = ['en', 'es', 'fr', 'ar', 'ru', 'zh']

BASE_FIELDS = [
    'id', 'link', 'type', 'status', 'number', 'treaty', 'published', 'updated',
    'meetingId', 'meetingTitle', 'meetingUrl'
]

MULTILANGUAL_FIELDS = ['title', 'longTitle']

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
regex = re.compile(r'[\n\t\r]')


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
    values = {}
    for result in info['results']:
        language = result['language']
        if language not in LANGUAGES:
            print(language, result['value'])
        value = regex.sub('', result['value'])
        values[language] = value
    return values


def parse_keywords(info):
    keywords = {}
    for result in info['results']:
        term = result['term']
        if term not in keywords:
            keywords[term] = True
    return list(keywords.keys()) or None


def parse_decisions(raw_decisions):
    decisions = []

    for raw_decision in raw_decisions:
        decision = {'type': 'decision'}

        for field in BASE_FIELDS:
            try:
                raw_decision[field] = int(raw_decision[field])
            except:
                pass
            decision[FIELD_MAP[field]] = raw_decision[field]

        if decision['decPublishDate']:
            date = get_date(decision['decPublishDate'])
            decision['decPublishDate'] = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if decision['decUpdateDate']:
            date = get_date(decision['decUpdateDate'])
            decision['decUpdateDate'] = date.strftime("%Y-%m-%dT%H:%M:%SZ")

        decision['decKeyword'] = parse_keywords(raw_decision['keywords'])

        for multi_field in MULTILANGUAL_FIELDS:
            multi_values = parse_multilangual(raw_decision[multi_field])
            field = FIELD_MAP[multi_field]
            for k, v in multi_values.items():
                field_name = field + '_' + k
                decision[field_name] = v

        dec_body = parse_multilangual(raw_decision['content'])
        decision['decBody'] = list(dec_body.values())

        decisions.append(decision)

    return decisions


def decision_needs_update(old, new):
    for field in FIELD_MAP.values():
        old_value = old.get(field, None)
        new_value = new.get(field, None)
        if old_value != new_value and old_value != [new_value]:
            return True
    return False


def add_decisions(decisions):
    solr = SolrWrapper()
    print(len(decisions))
    for decision in decisions:
        dec_id = int(decision['decId'])
        decision_result = solr.search_decision(dec_id)
        if decision_result:
            # CHECK AND UPDATE
            if decision_needs_update(decision_result, decision):
                dec_solr_id = decision_result['id']
                # solr.update_decision(dec_solr_id, decision)
                print('Decision %d has been updated' % (dec_id,))
            else:
                print('Decision %d already indexed' % (dec_id,))
        else:
            solr.add_decision(decision)
            print('Added: %d' % (int(decision['decId'])))


if __name__ == '__main__':
    raw_decisions = fetch_decisions()
    decisions = parse_decisions(raw_decisions)
    add_decisions(decisions)
