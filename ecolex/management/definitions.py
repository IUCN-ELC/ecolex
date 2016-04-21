COPY_FIELDS = [
    "trIntroText",
    "decTitleOfText",
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
    "docDate",
    "docLanguage_en",
    "docLanguage_fr",
    "docLanguage_es",
]

TREATY = 'treaty'
COP_DECISION = 'decision'
LEGISLATION = 'legislation'
COURT_DECISION = 'court_decision'
LITERATURE = 'literature'
LEGISLATION = 'legislation'

OBJ_TYPES = [TREATY, COP_DECISION, LEGISLATION, COURT_DECISION, LITERATURE]

DEC_TREATY_FIELDS = ['partyCountry_en', 'trSubject_en']

UNLIMITED_ROWS_COUNT = 999999
