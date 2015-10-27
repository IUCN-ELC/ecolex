DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
    ('literature', "Literature"),
    ('court_decision', "Court Decision"),
)

DOC_SOURCES = {
    'treaty': 'IUCN',
    'decision': 'InforMEA',
    'literature': 'ELIS',
    'court_decision': 'InforMEA',
}

TREATY_FILTERS = {
    'trTypeOfText': 'tr_type',
    'trFieldOfApplication': 'tr_field',
    'partyCountry': 'tr_party',
    'trRegion': 'tr_region',
    'trBasin': 'tr_basin',
    'trSubject': 'tr_subject',
    'trLanguageOfDocument': 'tr_language',
}

DECISION_FILTERS = {
    'decType': 'dec_type',
    'decStatus': 'dec_status',
    'decTreatyId': 'dec_treaty',
}

LITERATURE_FILTERS = {
    'litTypeOfText': 'lit_type',
    'litAuthor': 'lit_author',
    'litCountry': 'lit_country',
    'litRegion': 'lit_region',
    'litBasin': 'lit_basin',
    'litSerialTitle': 'lit_serial',
    'litPublisher': 'lit_publisher',
    'litSubject': 'lit_subject',
    'litLanguageOfDocument': 'lit_language',
}
COURT_DECISION_FILTERS = {
    'cdTypeOfText': 'cd_type',
    'cdLanguageOfDocument': 'cd_language',
}

DOC_TYPE_FILTER_MAPPING = {
    'treaty': TREATY_FILTERS,
    'decision': DECISION_FILTERS,
    'literature': LITERATURE_FILTERS,
    'court_decision': COURT_DECISION_FILTERS,
}

FIELD_TO_FACET_MAPPING = {
    'tr_type': 'trTypeOfText',
    'tr_field': 'trFieldOfApplication',
    'tr_party': 'partyCountry',
    'tr_region': 'trRegion',
    'tr_basin': 'trBasin',
    'tr_subject': 'trSubject',
    'tr_language': 'trLanguageOfDocument',

    'keyword': 'docKeyword',

    'dec_type': 'decType',
    'dec_status': 'decStatus',
    'dec_treaty': 'decTreatyId',

    'lit_type': 'litTypeOfText',
    'lit_author': 'litAuthor',
    'lit_country': 'litCountry',
    'lit_region': 'litRegion',
    'lit_basin': 'litBasin',
    'lit_serial': 'litSerialTitle',
    'lit_publisher': 'litPublisher',
    'lit_subject': 'litSubject',
    'lit_language': 'litLanguageOfDocument',

    'cd_type':  'cdTypeOfText',
    'cd_language': 'cdLanguageOfDocument',
}


SOLR_FIELDS = [
    'id', 'type', 'source', 'trTitleOfText', 'trJurisdiction',
    'trPlaceOfAdoption', 'trDateOfText', 'trDateOfEntry',
    'trDateOfModification', 'trPaperTitleOfText', 'trPaperTitleOfTextFr',
    'trPaperTitleOfTextSp', 'trPaperTitleOfTextOther', 'trTitleOfTextShort',
    'decTitleOfText', 'decStatus', 'decPublishDate', 'decUpdateDate',
    'decNumber',
    'litLongTitle', 'litLongTitle_fr', 'litLongTitle_sp', 'litLongTitle_other',
    'litPaperTitleOfText', 'litPaperTitleOfText_fr', 'litPaperTitleOfText_sp',
    'litPaperTitleOfText_other',
    'litTitleOfTextShort', 'litTitleOfTextShort_fr', 'litTitleOfTextShort_sp',
    'litTitleOfTextShort_other',
    'litTitleOfTextTransl', 'litTitleOfTextTransl_fr',
    'litTitleOfTextTransl_sp',
    'litDateOfEntry', 'litDateOfModifcation', 'litAbstract',
    'litTypeOfText',
    'litScope', 'litScope_fr', 'litScope_sp',
    'litAuthor', 'litCorpAuthor',
    'litPublisher', 'litPublPlace', 'litDateOfText',
    'litKeyword', 'litSeriesFlag',
    'litCountry', 'litRegion', 'litSubject', 'litLanguageOfDocument',
    'decNumber', 'cdTitleOfText_en', 'cdTitleOfText_es', 'cdTitleOfText_fr',
    'cdDateOfEntry', 'cdDateOfModification',
]

LANGUAGE_MAP = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'ru': 'Russian',
}
