
DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
)

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

DOC_TYPE_FILTER_MAPPING = {
    'treaty': TREATY_FILTERS,
    'decision': DECISION_FILTERS,
}
