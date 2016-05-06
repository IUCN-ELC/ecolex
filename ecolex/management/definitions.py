# The list below contains fields that are the destination of a copyField
# directive and also have the property stored=True. The list is used for
# cleaning up these fields, to prevent their multiplication on document update.
COPY_FIELDS = [
    "docDate",
    "docId",
    "docSubject_en",
    "docSubject_fr",
    "docSubject_es",
    "docKeyword_en",
    "docKeyword_fr",
    "docKeyword_es",
    "docCountry_en",
    "docCountry_fr",
    "docCountry_es",
    "docRegion_en",
    "docRegion_fr",
    "docRegion_es",
    "docLanguage_en",
    "docLanguage_fr",
    "docLanguage_es",
    "litAuthor",
]

TREATY = 'treaty'
COP_DECISION = 'decision'
LEGISLATION = 'legislation'
COURT_DECISION = 'court_decision'
LITERATURE = 'literature'

OBJ_TYPES = [TREATY, COP_DECISION, LEGISLATION, COURT_DECISION, LITERATURE]

DEC_TREATY_FIELDS = ['partyCountry_en', 'trSubject_en']

UNLIMITED_ROWS_COUNT = 999999
