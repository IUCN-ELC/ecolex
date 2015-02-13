""" Import treaties from XMLs exported by Elis
"""
import os

from bs4 import BeautifulSoup
import pysolr

from utils import get_text_tika


SCHEMA_FIELDS = [
    'trAbstract',
    'trAmendsTreaty', 'trAuthor', 'trAuthorA', 'trAuthorM',
    'trBasin', 'trCitesTreaty',
    'trComment', 'trConfName',
    'trConfPlace',
    'trContributor', 'trCorpAuthor', 'trCorpAuthorA',
    'trCorpAuthorM', 'trCountry', 'trCourtName',
    'trDateOfEntry',
    'trDateOfLastLegalAction', 'trDateOfModification',
    'trDateOfText', 'trDepository',
    'trDisplayDetails', 'trDisplayTitle', 'trEnabledByTreaty',
    'trEntryIntoForceDate', 'trFieldOfApplication',
    'trIntoForceTreaty', 'trIntOrg',
    'trJustices', 'trKeyword',
    'trLanguageOfDocument',
    'trLinkToFullText', 'trObsolete',
    'trPaperTitleOfText',
    'trPaperTitleOfTextStatement',
    'trPaperTitleOfTextTransl', 'trPlaceOfAdoption',
    'trPublisher',
    'trReferenceToCourtDecision', 'trReferenceToEULegislation',
    'trReferenceToFaolex', 'trReferenceToLiterature',
    'trReferenceToNationalLegislation', 'trReferenceToTreaties',
    'trRegion', 'trRelevantTextTreaty',
    'trScope', 'trSearchDate', 'trSeatOfCourt',
    'trSerialTitle',
    'trSortAuthor', 'trSortFieldOfApplication',
    'trSortTypeOfText', 'trSubject',
    'trSupersedesTreaty', 'trTerritorialSubdivision',
    'trTitleAbbreviation',
    'trTitleOfText', 'trTitleOfTextShort',
    'trTypeOfText',
]

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
    #'country': 'partyCountry',
    #'potentialparty': 'partyPotentialParty',
    #'entryintoforce': 'partyEntryIntoForce',
    #'dateofratification': 'partyDateOfRatification',
    #'dateofaccessionapprobation': 'partyDateOfAccessionApprobation',
    #'dateofacceptanceapproval': 'partyDateOfAcceptanceApproval',
    #'dateofconsenttobebound': 'partyDateOfConsentToBeBound',
    #'dateofsuccession': 'partyDateOfSuccession',
    #'dateofdefinitesignature': 'partyDateOfDefiniteSignature',
    #'dateofsimplesignature': 'partyDateOfSimpleSignature',
    #'dateofprovisionalapplication': 'partyDateOfProvisionalApplication',
    #'dateofparticipation': 'partyDateOfParticipation',
    #'dateofdeclaration': 'partyDateOfDeclaration',
    #'dateofreservation': 'partyDateOfReservation',
    #'dateofwithdrawal': 'partyDateOfWithdrawal',
}

PARTICIPANT_FIELDS = {
    'country': 'partyCountry',
    #'potentialparty': 'partyPotentialParty',
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

RICH_TEXT_DOCS = {}

TEXT_UPLOAD_ENABLED = 0

REFERENCE_MAPPING = {
    'trEnabledByTreaty': 'trEnablesTreaty',
    'trAmendsTreaty': 'trAmendedBy',
    'trSupersedesTreaty': 'trSupersededBy',
    'trCitesTreaty': 'trCitedBy',
}

def clean_text(text):
    return text.strip()


def missing_fields():
    return [f for f in SCHEMA_FIELDS if f not in FIELD_MAP.values()]


def valid_date(date):
    date_info = date.split('-')
    if len(date_info) != 3:
        return False
    if date_info[0] == '0000' or date_info[1] == '00' or date_info[2] == '00':
        return False
    return True


def party_format_date(date):
    if date == '':
        return date
    date_fields = date.split('-')
    for i in range(3 - len(date_fields)):
        date += "-01"
    return format_date(date)

def format_date(date):
    return date + "T00:00:00Z"


def solr_add_docs(solr, docs):
    solr.add(docs)
    solr.optimize()


def merge_informea_entry(solr, treaty, informea_id):
    result = solr.search('trInformeaId:' + informea_id)
    existing_fields = result.docs[0]
    existing_fields['source'] += ",elis"
    new_document = dict(list(treaty.items()) + list(existing_fields.items()))
    solr.delete('trInformeaId:' + informea_id)
    return new_document


def parse_xml(xml_path):
    bs = BeautifulSoup(open(xml_path, 'r', encoding='utf-8'))
    result = {}

    for document in bs.findAll('document'):
        data = {}
        #skip National treaties
        application_field = getattr(document, 'fieldofapplication')
        if application_field and application_field.text == 'National':
            continue
        
        for k, v in FIELD_MAP.items():
            field_values = document.findAll(k)
            if field_values:
                data[v] = [clean_text(field.text) for field in field_values]
                if v in DATE_FIELDS:
                    data[v] = [format_date(date) for date in data[v] if valid_date(date)]
        for party in document.findAll('party'):
            if not getattr(party, "country"):
                continue
            for k, v in PARTICIPANT_FIELDS.items():
                field = getattr(party, k)
                if not v in data:
                    data[v] = []
                if field:
                    clean_field = clean_text(field.text)
                    data[v].append(party_format_date(
                        clean_field) if v in DATE_FIELDS else clean_field)
                else:
                    data[v].append(format_date("0000-00-00"))
        
        # Special cases
        elis_id = data['trElisId'][0]
        if elis_id == "TRE-146817":
            data['trFieldOfApplication'] = ["Global", "Regional/restricted"]
        if elis_id == "TRE-149349":
            data['trDateOfText'] = format_date("2009-10-02") 

        if elis_id in RICH_TEXT_DOCS and TEXT_UPLOAD_ENABLED:
            data['doc_content'] = get_text_tika(RICH_TEXT_DOCS[elis_id])
        result[elis_id] = data

    return result


def generate_rich_text_mapping(root_directory):
    for root, dirs, files in os.walk(root_directory, topdown=False):
        for doc in files:
            RICH_TEXT_DOCS[doc.split('.')[0]] = os.path.join(root, doc)


def get_duplicate_ids(config_file):
    duplicates_mapping = {}
    with open(config_file) as f:
        for line in f:
            elis_id, informea_id = line.split()
            duplicates_mapping[elis_id] = informea_id

    return duplicates_mapping


def get_xml_abs_paths(root_directory):
    file_paths = []
    for root, dirs, files in os.walk(root_directory, topdown=False):
        for xml_file in files:
            file_paths.append(os.path.join(root, xml_file))
    return file_paths
 

def clean_referred_treaties(solr_docs):
    for elis_id, doc in solr_docs.items():
        for field_name in REFERENCE_MAPPING:
            if field_name in doc:
                doc[field_name] = [ref for ref in doc[field_name] if ref in solr_docs]
        solr_docs[elis_id] = dict((k, v) 
            for k, v in solr_docs[elis_id].items() if not isinstance(v, list) or any(v))
    

def add_back_links(solr_docs):
    for elis_id, doc in solr_docs.items():
        for orig_field, backlink_field in REFERENCE_MAPPING.items():
            if orig_field in doc:
                for reference in doc[orig_field]:
                    if reference in solr_docs:
                        solr_docs[reference].setdefault(backlink_field, [])
                        solr_docs[reference][backlink_field].append(elis_id)

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 4:
        print(
            "Usage: {} <xml_root_directory> <solr_adress> <collection_name>".format(
                sys.argv[0]))
        #mf = missing_fields()
        #pprint(mf)
        #print(len(mf), "values")
        sys.exit(0)

    xml_files = get_xml_abs_paths(sys.argv[1])
    solr = pysolr.Solr(
        "http://{}:8983/solr/{}".format(sys.argv[2], sys.argv[3]), timeout=10)

    duplicates_mapping = get_duplicate_ids("duplicates")
    generate_rich_text_mapping(
        "/home/anaion/nas/ecolex/xml_export_tools/files/treaties")

    new_solr_docs = {}
    for xml_file in xml_files:
        r = parse_xml(xml_file)

        for elis_id, treaty in r.items():
            if elis_id in duplicates_mapping.keys():
                print("update:" + duplicates_mapping[elis_id])
                merged_doc = merge_informea_entry(solr, treaty,
                                duplicates_mapping[elis_id])
                new_solr_docs[elis_id] = merged_doc
            else:
                treaty['type'] = 'treaty'
                treaty['source'] = 'elis'
                new_solr_docs[elis_id] = treaty
    
    clean_referred_treaties(new_solr_docs)
    add_back_links(new_solr_docs)
    solr_add_docs(solr, new_solr_docs.values())
