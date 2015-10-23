import requests

from bs4 import BeautifulSoup

from utils import EcolexSolr

ELIS_URL = "http://ecolex.ecolex.org:8083/ecolex/ledge/view/ExportResult"
EXPORT = "?exportType=xml&index=treaties"
FILTER = "searchDate_end=%d&searchDate_start=%d"
ORDER = "sortField=searchDate"
PAGE = "page=%d"

STOP_STRING = 'java.lang.NegativeArraySizeException'

FIELD_MAP = {
    'recid': 'trElisId',
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
    'country': 'trCountry',
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
    return False


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


def parse_treatries(raw_treaties):
    treaties = {}

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

    clean_referred_treaties(new_treaties)
    clean_referred_treaties(updated_treaties)
    add_back_links(new_treaties)
    add_back_links(updated_treaties)
    solr.add_bulk(new_treaties.values())
    solr.add_bulk(updated_treaties.values())
    print('Added %d new treaties' % (len(new_treaties)))
    print('Updated %d treaties' % (len(updated_treaties)))
    print('Already indexed treaties %d' % (already_indexed,))


if __name__ == '__main__':
    raw_treaties = fetch_treaties()
    treaties = parse_treatries(raw_treaties)
    add_treaties(treaties)
