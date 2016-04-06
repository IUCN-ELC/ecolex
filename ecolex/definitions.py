from .schema import FIELD_MAP, FILTER_FIELDS, FETCH_FIELDS, BOOST_FIELDS


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
    f.get_source_field('en'): k
    for k, f in FILTER_FIELDS.items()
    if k in FIELD_MAP['treaty']
}

DECISION_FILTERS = {
    f.get_source_field('en'): k
    for k, f in FILTER_FIELDS.items()
    if k in FIELD_MAP['decision']
}

LITERATURE_FILTERS = {
    f.get_source_field('en'): k
    for k, f in FILTER_FIELDS.items()
    if k in FIELD_MAP['literature']
}

COURT_DECISION_FILTERS = {
    f.get_source_field('en'): k
    for k, f in FILTER_FIELDS.items()
    if k in FIELD_MAP['court_decision']
}

LEGISLATION_FILTERS = {
    f.get_source_field('en'): k
    for k, f in FILTER_FIELDS.items()
    if k in FIELD_MAP['legislation']
}


DOC_TYPE_FILTER_MAPPING = {
    'treaty': TREATY_FILTERS,
    'decision': DECISION_FILTERS,
    'literature': LITERATURE_FILTERS,
    'court_decision': COURT_DECISION_FILTERS,
    'legislation': LEGISLATION_FILTERS,
}


FIELD_TO_FACET_MAPPING = {k: f.get_source_field('en')
                          for k, f in FILTER_FIELDS.items()}
SOLR_FIELDS = [f.get_source_field('en') for f in FETCH_FIELDS.values()]
RELEVANCY_FIELDS = {f.get_source_field('en'): f.solr_boost
                    for f in BOOST_FIELDS.values()}


_SELECT_FACETS = [
    # that is, facets thare are a <select> field...
    'xsubjects',
    'xkeywords',
    'xcountry',
    'xregion',
    'xlanguage',

    'tr_depository',
    'tr_place_of_adoption',

    'cd_territorial_subdivision',

    'dec_treaty_name',

    'leg_territorial_subdivision',

    'lit_author',
    'lit_orig_serial_title',
    'lit_publisher',
    'lit_type_of_text',
]

# TODO: get rid of this, and use above
SELECT_FACETS = {
    FIELD_TO_FACET_MAPPING[item]: item
    for item in _SELECT_FACETS
}

_CHECKBOX_FACETS = [
    'tr_type_of_document',
    'tr_field_of_application',
    'tr_status',

    'dec_type_of_document',
    'dec_status',

    'cd_type_of_document',

    'leg_type_of_document',
]

# all selection facets are OR-able, and so are all checkbox facets
_OR_OP_FACETS = _SELECT_FACETS + _CHECKBOX_FACETS
# NOTE: set(_OR_OP_FACETS) == set(FIELD_TO_FACET_MAPPING.keys()). go figure

# TODO: add all single-valued fields here / create clean list from multi-valued
_AND_OP_FACETS = set(_SELECT_FACETS).difference([
    'lit_publisher',
    'lit_orig_serial_title',
    'lit_type_of_text',
])

_AND_OP_FIELD_PATTERN = "%s_and_"
