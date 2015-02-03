""" Import treaties from XMLs exported by Elis
"""
from bs4 import BeautifulSoup
import pysolr
import os

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

PARTICIPANT_FIELDS = [
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

DATE_FIELDS = [
    'trDateOfEntry',
    'trDateOfModification',
    'trDateOfText',
    'trSearchDate',
    'trEntryIntoForceDate',
    'trDateOfLastLegalAction',
    'trSearchDate',
    #'partyEntryIntoForce',
    #'partyDateOfRatification',
    #'partyDateOfAccessionApprobation',
    #'partyDateOfAcceptanceApproval',
    #'partyDateOfConsentToBeBound',
    #'partyDateOfSuccession',
    #'partyDateOfDefiniteSignature',
    #'partyDateOfSimpleSignature',
    #'partyDateOfProvisionalApplication',
    #'partyDateOfParticipation',
    #'partyDateOfDeclaration',
    #'partyDateOfReservation',
    #'partyDateOfWithdrawal',
]

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
    return date + 'T00:00:00Z'

def parse_xml(path):
    bs = BeautifulSoup(open(path, 'r', encoding='utf-8'))
    result = []
    
    for document in bs.findAll('document'):
        data = {}
        for k, v in FIELD_MAP.items():
            field_values = document.findAll(k)
            if field_values:
                data[v] = [clean_text(field.text) for field in field_values] 
                if v in DATE_FIELDS:
                    data[v] = [format_date(date) for date in data[v]]
                
        result.append(data)
    
    return result

def add_docs(solr, docs):
    solr.add(docs)
    solr.optimize()

def update_solr_entry(solr, treaty, informea_id):
    result = solr.search('trInformeaId:' + informea_id)
    existing_fields = result.docs[0]
    existing_fields['source'] += ',elis'
    new_document = dict(list(treaty.items()) + list(existing_fields.items()))   
    solr.delete('trInformeaId:' + informea_id)
    add_docs(solr, [new_document])
 
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

    if len(sys.argv) < 3:
        print("Usage: {} <xml_root_directory> <solr_adress>".format(sys.argv[0]))
        mf = missing_fields()
        pprint(mf)
        print(len(mf), "values")
        sys.exit(0)

    xml_files = get_xml_abs_paths(sys.argv[1])
    solr = pysolr.Solr('http://{}:8983/solr/ecolex'.format(sys.argv[2]), timeout=10)
    
    duplicates_mapping = get_duplicate_ids("duplicates") 
   
    new_solr_docs = [] 
    for xml_file in xml_files:
        r = parse_xml(xml_file)
 
        for treaty in r:
            if treaty['trElisId'][0] in duplicates_mapping.keys():
                print('update:' + duplicates_mapping[treaty['trElisId'][0]])
                update_solr_entry(solr, treaty, duplicates_mapping[treaty['trElisId'][0]])
            else:
                treaty['type'] = 'treaty'
                treaty['source'] = 'elis'
                new_solr_docs.append(treaty)
    
    add_docs(solr, new_solr_docs) 
