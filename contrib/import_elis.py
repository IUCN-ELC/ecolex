""" Import treaties from XMLs exported by Elis
"""
from bs4 import BeautifulSoup
import pysolr

SCHEMA_FIELDS = [
    'trAbstract', 'trAbstractOther',
    'trAmendsTreaty', 'trAuthor', 'trAuthorA', 'trAuthorM',
    'trBasin', 'trCitesTreaty',
    'trComment', 'trCommentOther', 'trConfName',
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
    'trPaperTitleOfText', 'trPaperTitleOfTextOther',
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
    'trTitleOfText', 'trTitleOfTextOther', 'trTitleOfTextShort',
    'trTitleOfTextShortOther',
    'trTypeOfText',
]

FIELD_MAP = {
    'recid': 'trId',
    'dateofentry': 'trDateOfEntry',
    'dateofmodification': 'trDateOfModification',
    'dateoftext': 'trDateOfText',
    'searchdate': 'trSearchDate',
    'titleoftext': 'trPaperTitleOfText',
    'typeoftext': 'trTypeOfText',
    # 'jurisdiction': 'trJustices' maybe??
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
    'titleoftext': 'trTitleOfText',
    'author': 'trAuthor',

}


def clean_text(text):
    return text.strip()


def missing_fields():
    return [f for f in SCHEMA_FIELDS if f not in FIELD_MAP.values()]


def parse_xml(path):
    bs = BeautifulSoup(open(path, 'r'))
    result = []
    for document in bs.findAll('document'):
        data = {}
        for k, v in FIELD_MAP.items():
            field = getattr(document, k)
            data[v] = field and clean_text(field.text)
        result.append(data)
    return result


def find_existing(solr, treaty):
    """ Search in solr for an existing treaty
    """
    query = {
        'type': 'treaty',
        'trTitleOfText': treaty['trTitleOfText'],
    }
    query = ['{}:"{}"'.format(k, v.replace(" ", "\ ").replace(":", "\:")) for
             k, v in query.items()]
    # query = '{!lucene q.op=AND df=text}' + query
    result = solr.search("*", fq=query)
    print("*", query, "*")
    return result.hits#, [hit for hit in result]


if __name__ == '__main__':
    import sys
    from pprint import pprint

    if len(sys.argv) < 2:
        print("Usage: {} <filename.xml>".format(sys.argv[0]))
        mf = missing_fields()
        pprint(mf)
        print(len(mf), "values")
        sys.exit(0)

    solr = pysolr.Solr('http://10.0.0.98:8983/solr/ecolex', timeout=10)
    r = parse_xml(sys.argv[1])
    for treaty in r:
        print(treaty['trTitleOfText'][:25], "hits:",
              find_existing(solr, treaty))
