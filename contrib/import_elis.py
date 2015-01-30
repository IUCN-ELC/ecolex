""" Import treaties from XMLs exported by Elis
"""
from bs4 import BeautifulSoup

SCHEMA_FIELDS = [
    'trAbstract', 'trAbstractOther',
    'trAmendsTreaty', 'trAuthor', 'trAuthorA', 'trAuthorM',
    'trAuthorWhole', 'trBasin', 'trBasinWhole', 'trCitesTreaty',
    'trComment', 'trCommentOther', 'trConfName',
    'trConfNameWhole', 'trConfPlace', 'trConfPlaceWhole',
    'trContributor', 'trCorpAuthor', 'trCorpAuthorA',
    'trCorpAuthorM', 'trCountry', 'trCountryWhole', 'trCourtName',
    'trCourtNameWhole', 'trDateOfEntry',
    'trDateOfLastLegalAction', 'trDateOfModification',
    'trDateOfText', 'trDepository', 'trDepositoryWhole',
    'trDisplayDetails', 'trDisplayTitle', 'trEnabledByTreaty',
    'trEntryIntoForceDate', 'trFieldOfApplication',
    'trIntoForceTreaty', 'trIntOrg', 'trIntOrgWhole',
    'trJustices', 'trJusticesWhole', 'trKeyword',
    'trKeywordWhole', 'trLanguageOfDocument',
    'trLanguageOfDocumentWhole', 'trLinkToFullText', 'trObsolete',
    'trPaperTitleOfText', 'trPaperTitleOfTextOther',
    'trPaperTitleOfTextStatement',
    'trPaperTitleOfTextTransl', 'trPlaceOfAdoption',
    'trPlaceOfAdoptionWhole', 'trPublisher', 'trPublisherWhole',
    'trReferenceToCourtDecision', 'trReferenceToEULegislation',
    'trReferenceToFaolex', 'trReferenceToLiterature',
    'trReferenceToNationalLegislation', 'trReferenceToTreaties',
    'trRegion', 'trRegionWhole', 'trRelevantTextTreaty',
    'trScope', 'trSearchDate', 'trSeatOfCourt',
    'trSeatOfCourtWhole', 'trSerialTitle', 'trSerialTitleWhole',
    'trSortAuthor', 'trSortFieldOfApplication',
    'trSortTypeOfText', 'trSubject', 'trSubjectWhole',
    'trSupersedesTreaty', 'trTerritorialSubdivision',
    'trTerritorialSubdivisionWhole', 'trTitleAbbreviation',
    'trTitleOfText', 'trTitleOfTextOther', 'trTitleOfTextShort',
    'trTitleOfTextShortOther',
    'trTypeOfText', 'trTypeOfTextWhole'
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
    'titleoftextshort': 'titleOfTextShort',
    'titleoftext': 'titleOfText',
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


if __name__ == '__main__':
    import sys
    from pprint import pprint

    if len(sys.argv) < 2:
        print("Usage: {} <filename.xml>".format(sys.argv[0]))
        pprint(missing_fields())
        sys.exit(0)

    r = parse_xml(sys.argv[1])
    pprint(r)
