DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
    ('literature', "Literature"),
    ('court_decision', "Court Decision"),
    ('legislation', "Legislation"),
)

DOC_SOURCES = {
    'treaty': 'IUCN',
    'decision': 'InforMEA',
    'literature': 'IUCN',
    'court_decision': 'InforMEA',
    'legislation': 'FAO',
}

TREATY_FILTERS = {
    'trTypeOfText_en': 'tr_type',
    'trFieldOfApplication_en': 'tr_field',
    'trStatus': 'tr_status',
    'trPlaceOfAdoption': 'tr_place_of_adoption',
    'trDepository_en': 'tr_depository',
}

DECISION_FILTERS = {
    'decType': 'dec_type',
    'decStatus': 'dec_status',
    'decTreatyId': 'dec_treaty',
}

LITERATURE_FILTERS = {
    'litTypeOfText': 'lit_type',
    'litAuthor': 'lit_author',
    'litSerialTitle': 'lit_serial',
    'litPublisher': 'lit_publisher',
}

COURT_DECISION_FILTERS = {
    'cdTerritorialSubdivision': 'cd_territorial_subdivision',
    'cdTypeOfText': 'cd_type',
}

LEGISLATION_FILTERS = {
    'legType_en': 'leg_type',
    'legTerritorialSubdivision': 'leg_territorial',
    'legStatus': 'leg_status',
}

DOC_TYPE_FILTER_MAPPING = {
    'treaty': TREATY_FILTERS,
    'decision': DECISION_FILTERS,
    'literature': LITERATURE_FILTERS,
    'court_decision': COURT_DECISION_FILTERS,
    'legislation': LEGISLATION_FILTERS,
}

FIELD_TO_FACET_MAPPING = {
    'tr_type': 'trTypeOfText_en',
    'tr_field': 'trFieldOfApplication_en',
    'tr_status': 'trStatus',
    'tr_place_of_adoption': 'trPlaceOfAdoption',
    'tr_depository': 'trDepository_en',

    'dec_type': 'decType',
    'dec_status': 'decStatus',
    'dec_treaty': 'decTreatyId',

    'lit_type': 'litTypeOfText',
    'lit_author': 'litAuthor',
    'lit_serial': 'litSerialTitle',
    'lit_publisher': 'litPublisher',

    'cd_territorial_subdivision': 'cdTerritorialSubdivision',
    'cd_type': 'cdTypeOfText',

    'leg_type': 'legType_en',
    'leg_territorial': 'legTerritorialSubdivision',
    'leg_status': 'legStatus',

    'subject': 'docSubject',
    'keyword': 'docKeyword',
    'country': 'docCountry',
    'region': 'docRegion',
    'language': 'docLanguage',
}


SELECT_FACETS = {
    'docSubject': 'subject',
    'docKeyword': 'keyword',
    'docCountry': 'country',
    'docRegion': 'region',
    'docLanguage': 'language',

    'trDepository_en': 'tr_depository',
    'trPlaceOfAdoption': 'tr_place_of_adoption',

    'cdTerritorialSubdivision': 'cd_territorial_subdivision',

    'litAuthor': 'lit_author',
    'litSerialTitle': 'lit_serial',
    'litPublisher': 'lit_publisher',
}


OPERATION_FIELD_MAPPING = {
    'tr_depository_op': 'tr_depository',
    'lit_author_op': 'lit_author',
    'subject_op': 'subject',
    'keyword_op': 'keyword',
    'country_op': 'country',
    'region_op': 'region',
    'language_op': 'language',
}


SOLR_FIELDS = [
    'id', 'type', 'source', 'trTitleOfText', 'trJurisdiction_en', 'trStatus',
    'trPlaceOfAdoption', 'trDateOfText', 'trDateOfEntry',
    'trDateOfModification', 'trPaperTitleOfText_en', 'trPaperTitleOfText_fr',
    'trPaperTitleOfText_sp', 'trPaperTitleOfText_other', 'trTitleOfTextShort',
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
    'cdDateOfText', 'legTitle', 'legLongTitle', 'legCountry_en',
    'legDate', 'legStatus', 'legTerritorialSubdivision'
]

LANGUAGE_MAP = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'ru': 'Russian',
}
