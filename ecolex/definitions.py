
DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
    ('literature', "Literature"),
)

DOC_SOURCES = {
    'treaty': 'IUCN',
    'decision': 'InforMEA',
    'literature': 'ELIS'
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
    'litTypeOfText': 'lit_type'
}

DOC_TYPE_FILTER_MAPPING = {
    'treaty': TREATY_FILTERS,
    'decision': DECISION_FILTERS,
    'literature': LITERATURE_FILTERS,
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
    'litTypeOfText'
]
