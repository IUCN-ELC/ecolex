""" Import treaties from XMLs exported by Elis
"""
from bs4 import BeautifulSoup
import pysolr
import os
import requests
import socket, sys

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
    'confname':'trConfName',
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
BROKEN_DOCS_IDS = [
    'TRE-000077',
    'TRE-001214',
    'TRE-001953',
    'TRE-000155',
    'TRE-149568',
    'TRE-149655',
    'TRE-149799',
    'TRE-000565',
    'TRE-000566',
    'TRE-000567',
    'TRE-000569',
    'TRE-000570',
    'TRE-000887',
    'TRE-153643',
    'TRE-153648',
    'TRE-000781',
    'TRE-000733',
]

TEXT_UPLOAD_ENABLED = 1

def clean_text(text):
    return text.strip()

def missing_fields():
    return [f for f in SCHEMA_FIELDS if f not in FIELD_MAP.values()]

def format_date(date):
    if date == '':
        return date
    date_fields = date.split('-')
    for i in range(3-len(date_fields)):
        date += "-01"
    return date + "T00:00:00Z"

def add_docs(solr, docs):
    solr.add(docs)
    solr.optimize()

def update_solr_entry(solr, treaty, informea_id):
    result = solr.search('trInformeaId:' + informea_id)
    existing_fields = result.docs[0]
    existing_fields['source'] += ",elis"
    new_document = dict(list(treaty.items()) + list(existing_fields.items()))
    solr.delete('trInformeaId:' + informea_id)
    add_docs(solr, [new_document])

def get_text_tika(file_path):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1',1234))    
    f = open(file_path, 'rb')

    while True:
        chunk = f.read(65536)
        if not chunk:
            break
        s.sendall(chunk)

    s.shutdown(socket.SHUT_WR)
    
    file_content = ''
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        file_content += chunk.decode('utf-8')
    
    return file_content
    
def parse_xml(xml_path):
    bs = BeautifulSoup(open(xml_path, 'r', encoding='utf-8'))
    result = []
    
    for document in bs.findAll('document'):
        data = {}
        for k, v in FIELD_MAP.items():
            field_values = document.findAll(k)
            if field_values:
                data[v] = [clean_text(field.text) for field in field_values] 
                if v in DATE_FIELDS:
                    data[v] = [format_date(date) for date in data[v]]
        for party in document.findAll('party'):
            no_children = 0
            for child in party.children:
                no_children += 1
            if no_children == 1 and getattr(party, "potentialparty"):
                continue
            for k, v in PARTICIPANT_FIELDS.items():
                field = getattr(party, k)
                if not v in data:
                    data[v] = []    
                if field:
                    clean_field = clean_text(field.text)
                    data[v].append(format_date(clean_field) if v in DATE_FIELDS else clean_field)
                else:
                    data[v].append(format_date("0000-00-00"))
        elis_id = data['trElisId'][0]
        if elis_id in RICH_TEXT_DOCS and TEXT_UPLOAD_ENABLED:
            data['doc_content'] = get_text_tika(RICH_TEXT_DOCS[elis_id])
        result.append(data)
    
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

if __name__ == '__main__':
    import sys
    from pprint import pprint

    if len(sys.argv) < 4:
        print("Usage: {} <xml_root_directory> <solr_adress> <collection_name>".format(sys.argv[0]))
        #mf = missing_fields()
        #pprint(mf)
        #print(len(mf), "values")
        sys.exit(0)

    xml_files = get_xml_abs_paths(sys.argv[1])
    solr = pysolr.Solr("http://{}:8983/solr/{}".format(sys.argv[2], sys.argv[3]), timeout=10)
    
    duplicates_mapping = get_duplicate_ids("duplicates") 
    generate_rich_text_mapping("/home/anaion/nas/ecolex/xml_export_tools/files/treaties")
    
    new_solr_docs = [] 
    for xml_file in xml_files:
        r = parse_xml(xml_file)
 
        for treaty in r:
            if treaty['trElisId'][0] in duplicates_mapping.keys():
                print("update:" + duplicates_mapping[treaty['trElisId'][0]])
                update_solr_entry(solr, treaty, duplicates_mapping[treaty['trElisId'][0]])
            else:
                treaty['type'] = 'treaty'
                treaty['source'] = 'elis'
                new_solr_docs.append(treaty)
    
    add_docs(solr, new_solr_docs)
