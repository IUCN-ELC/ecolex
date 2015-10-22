import requests

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


def fetch_treaties():
    year_filter = FILTER % (2016, 1500)
    page = 109

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

        page += 1


if __name__ == '__main__':
    raw_treaties = fetch_treaties()
