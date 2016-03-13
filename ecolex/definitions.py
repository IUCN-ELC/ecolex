import collections

DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
    ('literature', "Literature"),
    ('court_decision', "Court Decision"),
    ('legislation', "Legislation"),
)

DOC_SOURCES = {
    'treaty': 'IUCN',
    'decision': 'UNEP',
    'literature': 'IUCN',
    'court_decision': 'UNEP',
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
    'decTreatyName_en': 'dec_treaty',
}

LITERATURE_FILTERS = {
    'litDisplayType_en': 'lit_type',
    'litTypeOfText_en': 'lit_type2',
    'litAuthor': 'lit_author',
    'litSerialTitle': 'lit_serial',
    'litPublisher': 'lit_publisher',
}

COURT_DECISION_FILTERS = {
    'cdTerritorialSubdivision_en': 'cd_territorial_subdivision',
    'cdTypeOfText': 'cd_type',
}

LEGISLATION_FILTERS = {
    'legType_en': 'leg_type',
    'legTerritorialSubdivision': 'leg_territorial',
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
    'dec_treaty': 'decTreatyName_en',

    'lit_author': 'litAuthor',
    'lit_serial': 'litSerialTitle',
    'lit_publisher': 'litPublisher',
    'lit_type': 'litDisplayType_en',
    'lit_type2': 'litTypeOfText_en',

    'cd_territorial_subdivision': 'cdTerritorialSubdivision_en',
    'cd_type': 'cdTypeOfText',

    'leg_type': 'legType_en',
    'leg_territorial': 'legTerritorialSubdivision',

    'subject': 'docSubject_en',
    'keyword': 'docKeyword_en',
    'country': 'docCountry_en',
    'region': 'docRegion_en',
    'language': 'docLanguage_en',
}


_SELECT_FACETS = [
    # that is, facets thare are a <select> field...
    'subject',
    'keyword',
    'country',
    'region',
    'language',

    'tr_depository',
    'tr_place_of_adoption',

    'cd_territorial_subdivision',

    'dec_treaty',

    'leg_territorial',

    'lit_author',
    'lit_serial',
    'lit_publisher',
    'lit_type',
    'lit_type2',
]

# TODO: get rid of this, and use above
SELECT_FACETS = {
    FIELD_TO_FACET_MAPPING[item]: item
    for item in _SELECT_FACETS
}

# TODO: why don't all SELECT_FACETS get an operator choice?
_AND_OP_FACETS = [
    # facets that are AND-able
    'subject',
    'keyword',
    'country',
    'region',
    'language',

    'tr_depository',

    'lit_author',
]

_AND_OP_FIELD_PATTERN = "%s_and_"
AND_OP_FIELD_MAPPING = {
    _AND_OP_FIELD_PATTERN % item: item
    for item in _AND_OP_FACETS
}


SOLR_FIELDS = [
    'id', 'type', 'source', 'trTitleOfText', 'trTypeOfText_en', 'trStatus',
    'trPlaceOfAdoption', 'trDateOfText', 'trDateOfEntry', 'trKeyword_en',
    'trDateOfModification', 'trPaperTitleOfText_en', 'trPaperTitleOfText_fr',
    'trPaperTitleOfText_es', 'trPaperTitleOfText_other', 'trTitleOfTextShort',
    'trElisId', 'decTreatyName_en',
    'decTitleOfText', 'decStatus', 'decPublishDate', 'decUpdateDate',
    'decShortTitle_en', 'decShortTitle_fr', 'decShortTitle_es',
    'decShortTitle_ru', 'decShortTitle_ar', 'decShortTitle_zh',
    'decNumber', 'docKeyword', 'cdKeywords',
    'decKeyword_en', 'decKeyword_fr', 'decKeyword_es',
    'litLongTitle_en', 'litLongTitle_fr', 'litLongTitle_es', 'litLongTitle_other',
    'litPaperTitleOfText_en', 'litPaperTitleOfText_fr', 'litPaperTitleOfText_es', 'litPaperTitleOfText_other',
    'litSerialTitle', 'litId',
    'litTitleOfTextShort_en', 'litTitleOfTextShort_fr', 'litTitleOfTextShort_es',
    'litTitleOfTextShort_other',
    'litTitleOfTextTransl_en', 'litTitleOfTextTransl_fr', 'litTitleOfTextTransl_es',
    'litDateOfEntry', 'litDateOfModification',
    'litAbstract_en', 'litAbstract_fr', 'litAbstract_es', 'litAbstract_other',
    'litTypeOfText_en', 'litTypeOfText_fr', 'litTypeOfText_es',
    'litScope_en', 'litScope_fr', 'litScope_es',
    'litAuthorArticle', 'litCorpAuthorArticle', 'litAuthor', 'litCorpAuthor',
    'litPublisher', 'litPublPlace', 'litDateOfText',
    'litKeyword_en', 'litSeriesFlag',
    'litCountry_en', 'litRegion', 'litSubject_en',
    'litLanguageOfDocument_en', 'litLanguageOfDocument_fr', 'litLanguageOfDocument_es',
    'cdTitleOfText_en', 'cdTitleOfText_es', 'cdTitleOfText_fr',
    'cdTypeOfText', 'cdCountry_en', 'cdDateOfText',
    'legTitle', 'legLongTitle', 'legCountry_en', 'legKeyword_en',
    'legYear', 'legOriginalYear', 'legStatus', 'legTerritorialSubdivision', 'legId',
]

LANGUAGE_MAP = collections.OrderedDict([
    ('en', 'English'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('ru', 'Russian'),
    ('other', 'Other'),
])
