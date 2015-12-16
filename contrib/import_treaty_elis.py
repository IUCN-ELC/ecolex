import requests
import sys
from binascii import hexlify
from bs4 import BeautifulSoup

from utils import EcolexSolr, get_file_from_url, DEC_TREATY_FIELDS

ELIS_URL = "http://ecolex.ecolex.org:8083/ecolex/ledge/view/ExportResult"
EXPORT = "?exportType=xml&index=treaties"
FILTER = "searchDate_end=%d&searchDate_start=%d"
ORDER = "sortField=searchDate"
PAGE = "page=%d"

STOP_STRING = 'java.lang.NegativeArraySizeException'
NO_MATCHES = 'No matches found'

FIELD_MAP = {
    'recid': 'trElisId',
    'informeauid': 'trInformeaId',
    'dateofentry': 'trDateOfEntry',
    'dateofmodification': 'trDateOfModification',
    'dateoftext': 'trDateOfText',
    'searchdate': 'trSearchDate',
    'titleoftext': 'trPaperTitleOfText',
    'titleoftextsp': 'trPaperTitleOfTextSp',
    'titleoftextfr': 'trPaperTitleOfTextFr',
    'titleoftextother': 'trPaperTitleOfTextOther',
    'typeoftext': 'trTypeOfText',
    'jurisdiction': 'trJurisdiction',
    'fieldofapplication': 'trFieldOfApplication',
    'subject': 'trSubject',
    'languageofdocument': 'trLanguageOfDocument',
    'obsolete': 'trObsolete',
    'enabledbytreaty': 'trEnabledByTreaty',
    'placeofadoption': 'trPlaceOfAdoption',
    'depository': 'trDepository',
    'entryintoforcedate': 'trEntryIntoForceDate',
    'keyword': 'trKeyword',
    'abstract': 'trAbstract',
    'comment': 'trComment',
    'titleoftextshort': 'trTitleOfTextShort',
    'author': 'trAuthor',
    'titleabbreviation': 'trTitleAbbreviation',
    'fieldofapplication': 'trFieldOfApplication',
    'placeofadoption': 'trPlaceOfAdoption',
    'basin': 'trBasin',
    'citiestreaty': 'trCitiesTreaty',
    'confname': 'trConfName',
    'contributor': 'trContributor',
    'courtname': 'trCourtName',
    'dateoflastlegalaction': 'trDateOfLastLegalAction',
    'linktofulltext': 'trLinkToFullText',
    'linktofulltextsp': 'trLinkToFullTextSp',
    'linktofulltextfr': 'trLinkToFullTextFr',
    'linktofulltextother': 'trLinkToFullTextOther',
    'linktoabstract': 'trLinkToAbstract',
    'obsolete': 'trObsolete',
    'region': 'trRegion',
    'relevanttexttreaty': 'trRelevantTextTreaty',
    'scope': 'trScope',
    'searchdate': 'trSearchDate',
    'seatofcourt': 'trSeatOfCourt',
    'supersedestreaty': 'trSupersedesTreaty',
    'amendstreaty': 'trAmendsTreaty',
    'citestreaty': 'trCitesTreaty',
    'availablein': 'trAvailableIn',
    'languageoftranslation': 'trLanguageOfTranslation',
    'numberofpages': 'trNumberOfPages',
    'officialPublication': 'trOfficialPublication',
    'InternetReference': 'trInternetReference',
    'dateofconsolidation': 'trDateOfConsolidation',
}

PARTICIPANT_FIELDS = {
    'country': 'partyCountry',
    'entryintoforce': 'partyEntryIntoForce',
    'dateofratification': 'partyDateOfRatification',
    'dateofaccessionapprobation': 'partyDateOfAccessionApprobation',
    'dateofacceptanceapproval': 'partyDateOfAcceptanceApproval',
    'dateofconsenttobebound': 'partyDateOfConsentToBeBound',
    'dateofsuccession': 'partyDateOfSuccession',
    'dateofdefinitesignature': 'partyDateOfDefiniteSignature',
    'dateofsimplesignature': 'partyDateOfSimpleSignature',
    'dateofprovisionalapplication': 'partyDateOfProvisionalApplication',
    'dateofparticipation': 'partyDateOfParticipation',
    'dateofdeclaration': 'partyDateOfDeclaration',
    'dateofreservation': 'partyDateOfReservation',
    'dateofwithdrawal': 'partyDateOfWithdrawal',
}

DATE_FIELDS = [
    'trDateOfEntry',
    'trDateOfModification',
    'trDateOfText',
    'trSearchDate',
    'trEntryIntoForceDate',
    'trDateOfLastLegalAction',
    'trSearchDate',
    'trDateOfConsolidation',
    'partyEntryIntoForce',
    'partyDateOfRatification',
    'partyDateOfAccessionApprobation',
    'partyDateOfAcceptanceApproval',
    'partyDateOfConsentToBeBound',
    'partyDateOfSuccession',
    'partyDateOfDefiniteSignature',
    'partyDateOfSimpleSignature',
    'partyDateOfProvisionalApplication',
    'partyDateOfParticipation',
    'partyDateOfDeclaration',
    'partyDateOfReservation',
    'partyDateOfWithdrawal',
]

REFERENCE_MAPPING = {
    'trEnabledByTreaty': 'trEnablesTreaty',
    'trAmendsTreaty': 'trAmendedBy',
    'trSupersedesTreaty': 'trSupersededBy',
    'trCitesTreaty': 'trCitedBy',
}

URL_FIELDS = [
    'linktofulltext', 'linktofulltextsp', 'linktofulltextfr',
    'linktofulltextother'
]


def clean_text(text):
    return text.strip()


def valid_date(date):
    date_info = date.split('-')
    if len(date_info) != 3:
        return False
    if date_info[0] == '0000' or date_info[1] == '00' or date_info[2] == '00':
        return False
    return True


def format_date(date):
    return date + "T00:00:00Z"


def party_format_date(date):
    if date == '':
        return date
    date_fields = date.split('-')
    for i in range(3 - len(date_fields)):
        date += "-01"
    return format_date(date)


def clean_referred_treaties(solr_docs):
    for elis_id, doc in solr_docs.items():
        for field_name in REFERENCE_MAPPING:
            if field_name in doc:
                doc[field_name] = [ref for ref in doc[field_name]
                                   if ref in solr_docs]
        solr_docs[elis_id] = dict((k, v)
                                  for k, v in solr_docs[elis_id].items()
                                  if not isinstance(v, list) or any(v))


def add_back_links(solr_docs):
    for elis_id, doc in solr_docs.items():
        for orig_field, backlink_field in REFERENCE_MAPPING.items():
            if orig_field in doc:
                for reference in doc[orig_field]:
                    if reference in solr_docs:
                        solr_docs[reference].setdefault(backlink_field, [])
                        solr_docs[reference][backlink_field].append(elis_id)


def treaty_needs_update(old, new):
    for field in FIELD_MAP.values():
        old_value = old.get(field, None)
        new_value = new.get(field, None)
        if new_value == ['false'] or (new_value == [] and not old_value):
            continue
        if (old_value != new_value and old_value != [new_value] and
           [old_value] != new_value):
            return True
    return False


def update_decisions(solr, treaty):
    if not treaty.get('trInformeaId'):
        return

    decisions = solr.search_all('decTreatyId', treaty['trInformeaId'])
    if not decisions:
        return

    for decision in decisions:
        for field in DEC_TREATY_FIELDS:
            decision[field] = treaty[field]
    solr.add(decisions)


def fetch_treaties():
    year_filter = FILTER % (2016, 1500)
    page = 0
    treaties = []

    while True:
        print(page)
        page_filter = PAGE % (page, )
        query = '%s%s&%s&%s&%s' % (ELIS_URL, EXPORT, year_filter, ORDER,
                                   page_filter)

        response = requests.get(query)
        if response.status_code != 200:
            raise ValueError('Invalid return code %d' % response.status_code)

        if STOP_STRING in str(response.content):
            break

        treaties.append(response.content)

        page += 1

    return treaties


def fetch_treaties_2():
    URL = 'http://www.ecolex.org/elis_isis3w.php'
    EXPORT = '?database=tre&search_type=page_search&table=all'
    query_filter = '&spage_query=%s'
    query_format = 'ES:I AND STAT:C AND DE:%d*'

    FORMAT = '&format_name=@xmlexp&lang=xmlf&page_header=@xmlh'
    page_filter = '&spage_first=%d'
    per_page = 20

    start_year = 1981
    end_year = 2015

    treaties = []
    for year in range(start_year, end_year):
        skip = 0
        query_year = query_format % (year)
        query_hex = hexlify(str.encode(query_year)).decode()
        query = query_filter % (query_hex)
        page = page_filter % (skip)

        url = '%s%s%s%s%s' % (URL, EXPORT, query, FORMAT, page)
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError('Invalid return code %d' % response.status_code)
        bs = BeautifulSoup(response.content)
        if bs.find('error'):
            continue

        treaties.append(response.content)
        documents_found = int(bs.find('result').attrs['numberresultsfound'])
        if documents_found > per_page:
            while skip < documents_found - per_page:
                skip += 20
                page = page_filter % (skip)
                url = '%s%s%s%s%s' % (URL, EXPORT, query, FORMAT, page)
                response = requests.get(url)
                if response.status_code != 200:
                    raise ValueError('Invalid return code %d'
                                     % response.status_code)
                treaties.append(response.content)

        print(year, documents_found)

    return treaties


def parse_treatries(raw_treaties):
    treaties = {}
    solr = EcolexSolr()

    for raw_treaty in raw_treaties:
        bs = BeautifulSoup(raw_treaty)
        for document in bs.findAll('document'):
            data = {
                'type': 'treaty',
                'source': 'elis'
            }
            for k, v in FIELD_MAP.items():
                field_values = document.findAll(k)
                if field_values:
                    data[v] = [clean_text(f.text) for f in field_values]
                    if v in DATE_FIELDS:
                        data[v] = [format_date(date) for date in data[v] if
                                   valid_date(date)]

            for party in document.findAll('party'):
                if not getattr(party, 'country'):
                    continue
                for k, v in PARTICIPANT_FIELDS.items():
                    field = getattr(party, k)
                    if v not in data:
                        data[v] = []
                    if field:
                        clean_field = clean_text(field.text)
                        data[v].append(party_format_date(
                            clean_field) if v in DATE_FIELDS else clean_field)
                    else:
                        data[v].append(format_date('0000-00-00'))

            data['text'] = ''
            for field in URL_FIELDS:
                value = document.find(field)
                if value:
                    url = value.text
                    file_obj = get_file_from_url(url)
                    data['text'] += solr.extract(file_obj)
            elis_id = data['trElisId'][0]
            if elis_id == 'TRE-146817':
                data['trFieldOfApplication'] = ['Global',
                                                'Regional/restricted']
            elif elis_id == 'TRE-149349':
                data['trDateOfText'] = format_date('2009-10-02')

            treaties[elis_id] = data

    return treaties


def add_treaties(treaties):
    solr = EcolexSolr()

    new_treaties = {}
    updated_treaties = {}
    already_indexed = 0
    for elis_id, treaty in treaties.items():
        treaty_result = solr.search('Treaty', elis_id)
        if treaty_result:
            if treaty_needs_update(treaty_result, treaty):
                treaty['id'] = treaty_result['id']
                updated_treaties[elis_id] = treaty
                print('Treaty %s has been updated' % (elis_id,))
            else:
                print('Treaty %s already indexed' % (elis_id),)
                already_indexed += 1
        else:
            new_treaties[elis_id] = treaty
            print('Added %s' % (elis_id),)

        update_decisions(solr, treaty)

    clean_referred_treaties(new_treaties)
    clean_referred_treaties(updated_treaties)
    add_back_links(new_treaties)
    add_back_links(updated_treaties)
    solr.add_bulk(new_treaties.values())
    solr.add_bulk(updated_treaties.values())
    print('Added %d new treaties' % (len(new_treaties)))
    print('Updated %d treaties' % (len(updated_treaties)))
    print('Already indexed treaties %d' % (already_indexed,))


def update_treaties_status():
    """Updates the status of already indexed treaties"""
    solr = EcolexSolr()
    rows = 50
    start = 0
    treaties_updated = []
    while True:
        print(start)
        treaties = solr.solr.search('type:treaty', rows=rows, start=start)
        for treaty in treaties:
            if 'trEntryIntoForceDate' not in treaty:
                treaty['trStatus'] = 'Not in force'
            else:
                if 'trSupersededBy' in treaty:
                    treaty['trStatus'] = 'Superseded'
                else:
                    treaty['trStatus'] = 'In force'
            treaties_updated.append(treaty)

        if len(treaties) < rows:
            break
        start += rows
    solr.add_bulk(treaties_updated)

if __name__ == '__main__':
    fetch_treaties_2()
    # if len(sys.argv) > 1 and 'update_status' in sys.argv:
    #     update_treaties_status()
    # else:
    #     raw_treaties = fetch_treaties()
    #     treaties = parse_treatries(raw_treaties)
    #     add_treaties(treaties)
