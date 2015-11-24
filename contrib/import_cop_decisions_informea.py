""" Import COP Decisions from Informea OData and update Solr index
"""
import re
import requests
import sys
from datetime import date, timedelta

from utils import get_date, get_file_from_url, EcolexSolr, DEC_TREATY_FIELDS


ODATA_URL = "http://odata.informea.org/informea.svc/Decisions"
BULK = "$top=%d&$skip=%d"

FILTER = "$filter=updated gt datetime'%s'"
DUMMY_DATE = '2000-01-01T00:00:00'

FORMAT = '$format=json'
EXPAND = '$expand=title,longTitle,keywords,content,files'
ORDER = '$orderby=updated asc'

LANGUAGES = ['en', 'es', 'fr', 'ar', 'ru', 'zh']
DEFAULT_LANG = 'en'

BASE_FIELDS = [
    'id', 'link', 'type', 'status', 'number', 'treaty', 'published', 'updated',
    'meetingId', 'meetingTitle', 'meetingUrl', 'treatyUUID'
]
MULTILANGUAL_FIELDS = ['title', 'longTitle']

FIELD_MAP = {
    'id': 'decId',
    'link': 'decLink',

    'title': 'decShortTitle',
    'longTitle': 'decLongTitle',
    'keywords': 'decKeyword',
    'summary': 'decSummary',
    'content': 'decBody',
    'type': 'decType',
    'status': 'decStatus',
    'number': 'decNumber',

    'treaty': 'decTreaty',
    'treatyUUID': 'decTreatyId',

    'published': 'decPublishDate',
    'updated': 'decUpdateDate',

    'meetingId': 'decMeetingId',
    'meetingTitle': 'decMeetingTitle',
    'meetingUrl': 'decMeetingUrl',
}
regex = re.compile(r'[\n\t\r]')


def fetch_decisions(limit=100, days_ago=7):
    # THE CRON WILL RUN WEEKLY, SO WE CHECK THE UPDATES FOR THE LAST WEEK
    today = date.today()
    last_update = today - timedelta(days_ago)
    date_filter = FILTER % (last_update.strftime("%Y-%m-%dT00:00:00"), )

    decisions = []
    skip = 0
    while True:
        print(skip)
        bulk = BULK % (limit, skip)

        query = '%s?%s&%s&%s&%s&%s' % (ODATA_URL, bulk, FORMAT, EXPAND,
                                       date_filter, ORDER)
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
            continue
        value = regex.sub('', result['value'])
        values[language] = value.strip()
    return values


def parse_keywords(info):
    keywords = {}
    for result in info['results']:
        term = result['term']
        if term not in keywords:
            keywords[term] = True
    return list(keywords.keys()) or None


def parse_files(solr, files):
    languages = set()
    text = ''
    for file_dict in files:
        lang = file_dict.get('language')
        languages.add(lang if lang not in (None, 'und') else DEFAULT_LANG)

        file_obj = get_file_from_url(file_dict['url'])
        text += solr.extract(file_obj)
    return languages, text


def parse_decisions(raw_decisions):
    decisions = []
    solr = EcolexSolr()

    for raw_decision in raw_decisions:
        decision = {'type': 'decision'}

        for field in BASE_FIELDS:
            try:
                raw_decision[field] = raw_decision[field].strip()
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

        files = raw_decision['files']['results']
        if files:
            decision['text'], decision['decLanguage'] = parse_files(solr, files)

        if decision['decTreatyId']:
            treaties = solr.search_all('trInformeaId', decision['decTreatyId'])
            if treaties:
                for field in DEC_TREATY_FIELDS:
                    decision[field] = [treaty[field] for treaty in treaties]

        decisions.append(decision)

    return decisions


def decision_needs_update(old, new):
    for field in FIELD_MAP.values():
        old_value = old.get(field, None)
        new_value = new.get(field, None)
        if not (old_value or new_value) or field == 'decUpdateDate':
            continue
        if (field == 'decBody' and set(old_value) == set(new_value)):
            continue
        if (old_value != new_value and old_value != [new_value]):
            return True
    return False


def add_decisions(decisions):
    solr = EcolexSolr()
    new_decisions = []
    updated_decisions = []
    already_indexed = 0

    for decision in decisions:
        dec_id = decision['decId']
        decision_result = solr.search('COP Decision', dec_id)
        if decision_result:
            # CHECK AND UPDATE
            if decision_needs_update(decision_result, decision):
                decision['id'] = decision_result['id']
                updated_decisions.append(decision)
                print('Decision %s has been updated' % (dec_id,))
            else:
                print('Decision %s already indexed' % (dec_id,))
                already_indexed += 1
        else:
            new_decisions.append(decision)
            print('Added: %s' % (decision['decId']))

    solr.add_bulk(new_decisions)
    solr.add_bulk(updated_decisions)
    print('Added %d new decisions' % (len(new_decisions)))
    print('Updated %d decisions' % (len(updated_decisions)))
    print('Already indexed decisions %d' % (already_indexed,))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        raw_decisions = fetch_decisions(days_ago=99999)
    else:
        raw_decisions = fetch_decisions()
    decisions = parse_decisions(raw_decisions)
    add_decisions(decisions)
