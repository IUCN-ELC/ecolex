"""
Usage:

>>> lschema = schema.LegislationSchema()
>>> lschema.context={'language': 'fr'}
>>> result, errors = lschema.load({'id': 'abc', 'legCountry_fr': 'xyz'})
>>> result
{'country': 'xyz', 'id': 'abc'}

"""

from collections import OrderedDict, defaultdict, namedtuple
from marshmallow import post_load, pre_load

from ecolex.lib.schema import Schema, fields
from ecolex.solr_models_re import (
    CourtDecision, Decision, Legislation, Literature, Treaty, TreatyParty,
)


class BaseSchema(Schema):
    """
    Inherited by all main object schemas.
    """

    id = fields.String()
    type = fields.String()
    source = fields.String()
    indexed_at = fields.DateTime(load_from='indexedDate')
    updated_at = fields.DateTime(load_from='updatedDate')

    text = fields.List(fields.String())
    # skipping this momentarily because it's not indexed
    # doc_content = fields.List(fields.String())

    # common fields, used for filtering / faceting
    # TODO: redundant with CommonSchema below?
    xkeywords = fields.List(fields.String(),
                            load_from='docKeyword',
                            multilingual=True)
    xsubjects = fields.List(fields.String(),
                            load_from='docSubject',
                            multilingual=True)
    xcountry = fields.String(load_from='docCountry',
                             multilingual=True)
    xregion = fields.String(load_from='docRegion',
                            multilingual=True)
    xlanguage = fields.String(load_from='docLanguage',
                              multilingual=True)

    xdate = fields.Date(load_from='docDate')

    text = fields.List(fields.String())
    # skipping this momentarily because it's not indexed. TODO.
    # doc_content = fields.List(fields.String())

    class Meta:
        solr_filters = [
            'type', 'xkeywords', 'xsubjects', 'xcountry', 'xregion',
            'xlanguage', 'xdate',
        ]
        solr_fetch = [
            'id', 'type', 'source',
        ]
        solr_boost = {
            'text': 20,
            #'doc_content': 10, # not indexed, see above
        }

    @post_load
    def make_model(self, data):
        if self.opts.model:
            return self.opts.model(**data)
        else:
            return data

class CommonSchema(BaseSchema):
    # Common fields that have different names in Solr
    # TODO: merge document ids appropriately on the import side
    document_id = fields.String(load_from_attribute='ID_FIELD')
    keywords = fields.List(fields.String(), multilingual=True,
                           load_from_attribute='KEYWORDS_FIELD')
    subjects = fields.List(fields.String(), multilingual=True,
                           load_from_attribute='SUBJECTS_FIELD')

    class Meta:
        solr_fetch = [
            'document_id', 'keywords', 'subjects',
        ]
        solr_boost = {
            'document_id': 100,
            'keywords': 30,
        }


class TreatyPartySchema(Schema):
    country = fields.String(load_from='partyCountry', multilingual=True)
    acceptance_approval = fields.Date(load_from='partyDateOfAcceptanceApproval')
    accession_approbation = fields.Date(
        load_from='partyDateOfAccessionApprobation')
    consent_to_be_bound = fields.Date(load_from='partyDateOfConsentToBeBound')
    definite_signature = fields.Date(load_from='partyDateOfDefiniteSignature')
    entry_into_force = fields.Date(load_from='partyEntryIntoForce', missing=None)
    participation = fields.Date(load_from='partyDateOfParticipation')
    provisional_application = fields.Date(
        load_from='partyDateOfProvisionalApplication')
    ratification = fields.Date(load_from='partyDateOfRatification')
    reservation = fields.Date(load_from='partyDateOfReservation')
    simple_signature = fields.Date(load_from='partyDateOfSimpleSignature')
    succession = fields.Date(load_from='partyDateOfSuccession')
    withdrawal = fields.Date(load_from='partyDateOfWithdrawal')

    @post_load
    def make_model(self, data):
        return TreatyParty(**data)


class TreatySchema(CommonSchema):
    ID_FIELD = 'trElisId'
    KEYWORDS_FIELD = 'trKeyword'
    SUBJECTS_FIELD = 'trSubject'

    class Meta:
        model = Treaty
        abbr = 'tr'
        type = 'treaty'
        solr_filters = [
            'type_of_document', 'depository', 'field_of_application',
            'place_of_adoption', 'status',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'title_of_text', 'status', 'place_of_adoption',
            'date_of_entry', 'date_of_text', 'date_of_modification',
            'paper_title_of_text', 'paper_title_of_text_other',
            'title_of_text_short', 'type_of_document',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'paper_title_of_text': 110,
            'title_abbreviation': 75,
            'abstract': 50,
            'basin': 25,
            'region': 25,
        })

    # TODO: False list (?)
    type_of_document = fields.List(fields.String(),
                                   load_from='trTypeOfText',
                                   multilingual=True)

    parties = fields.Nested(TreatyPartySchema, many=True)

    abstract = fields.List(fields.String(), load_from='trAbstract',
                           multilingual=True)
    author = fields.List(fields.String(), load_from='trAuthor')
    author_a = fields.List(fields.String(), load_from='trAuthorA')
    author_m = fields.List(fields.String(), load_from='trAuthorM')
    author_whole = fields.List(fields.String(), load_from='trAuthorWhole')
    available_in = fields.List(fields.String(), load_from='trAvailableIn')  # False list
    basin = fields.List(fields.String(), load_from='trBasin', multilingual=True)
    comment = fields.List(fields.String(), load_from='trComment')
    conf_name = fields.List(fields.String(), load_from='trConfName')
    conf_place = fields.List(fields.String(), load_from='trConfPlace')
    contributor = fields.List(fields.String(), load_from='trContributor')
    court_name = fields.List(fields.String(), load_from='trCourtName')
    date_of_consolidation = fields.List(fields.Date(),
                                        load_from='trDateOfConsolidation')
    date_of_entry = fields.Date(load_from='trDateOfEntry', missing=None)
    date_of_last_legal_action = fields.Date(load_from='trDateOfLastLegalAction')
    date_of_modification = fields.Date(load_from='trDateOfModification',
                                       missing=None)
    date_of_text = fields.Date(load_from='trDateOfText', missing=None)
    depository = fields.List(fields.String(),
                             load_from='trDepository',
                             multilingual=True)
    enabled = fields.String(load_from='trEnabled')
    entry_into_force_date = fields.Date(load_from='trEntryIntoForceDate')
    field_of_application = fields.List(fields.String(),
                                       load_from='trFieldOfApplication',
                                       multilingual=True)

    informea_id = fields.String(load_from='trInformeaId')
    internet_reference = fields.List(fields.String(),
                                     load_from='trInternetReference',
                                     multilingual=True)
    internet_reference_other = fields.List(
        fields.String(), load_from='trInternetReference_other')
    into_force_treaty = fields.List(fields.String(),
                                    load_from='trIntoForceTreaty')
    intro_text = fields.List(fields.String(), load_from='trIntroText')
    is_protocol = fields.String(load_from='trIsProtocol')
    jurisdiction = fields.List(fields.String(), load_from='trJurisdiction',
                               multilingual=True)
    language_of_document = fields.List(fields.String(),
                                       load_from='trLanguageOfDocument',
                                       multilingual=True)
    language_of_translation = fields.List(fields.String(),
                                          load_from='trLanguageOfTranslation')
    link_to_abstract = fields.List(fields.String(),
                                   load_from='trLinkToAbstract')
    link_to_full_text = fields.List(fields.String(),
                                    load_from='trLinkToFullText',
                                    multilingual=True)
    link_to_full_text_other = fields.List(fields.String(),
                                          load_from='trLinkToFullText_other')
    logo_medium = fields.String(load_from='trLogoMedium')
    number_of_pages = fields.List(fields.String(), load_from='trNumberOfPages')
    number_of_parties = fields.List(fields.String(),
                                    load_from='trNumberOfParties')
    official_publication = fields.List(fields.String(),
                                       load_from='trOfficialPublication')
    order = fields.String(load_from='trOrder')
    paper_title_of_text = fields.List(fields.String(),
                                      load_from='trPaperTitleOfText',
                                      multilingual=True,
                                      missing=[])
    paper_title_of_text_other = fields.List(
        fields.String(), load_from='trPaperTitleOfText_other')
    parent_id = fields.Integer(load_from='trParentId')
    # TODO: False list
    place_of_adoption = fields.List(fields.String(),
                                    load_from='trPlaceOfAdoption')
    primary = fields.List(fields.String(), load_from='trPrimary')
    region = fields.List(fields.String(), load_from='trRegion',
                         multilingual=True)
    relevant_text_treaty = fields.List(fields.String(),
                                       load_from='trRelevantTextTreaty')
    scope = fields.List(fields.String(), load_from='trScope')
    search_date = fields.Date(load_from='trSearchDate')
    seat_of_court = fields.List(fields.String(), load_from='trSeatOfCourt')
    status = fields.String(load_from='trStatus')
    theme_secondary = fields.List(fields.String(), load_from='trThemeSecondary')
    title_abbreviation = fields.List(fields.String(),
                                     load_from='trTitleAbbreviation')
    title_of_text = fields.List(fields.String(), load_from='trTitleOfText',
                                missing=[])
    title_of_text_short = fields.List(fields.String(),
                                      load_from='trTitleOfTextShort')  # False list
    url = fields.List(fields.String(), load_from='trUrl')
    url_elearning = fields.List(fields.String(), load_from='trUrlElearning')
    url_parties = fields.List(fields.String(), load_from='trUrlParties')
    url_treaty_text = fields.List(fields.String(), load_from='trUrlTreatyText')
    url_wikipedia = fields.List(fields.String(), load_from='trUrlWikipedia')

    # References
    amends = fields.List(fields.String(), load_from='trAmendsTreaty')
    cites = fields.List(fields.String(), load_from='trCitesTreaty')
    enabled_by = fields.List(fields.String(), load_from='trEnabledByTreaty')
    supersedes = fields.List(fields.String(), load_from='trSupersedesTreaty')

    @pre_load
    def handle_parties(self, data):
        parties = OrderedDict((k, v) for k, v in data.items()
                              if k.startswith('party'))
        parties = [dict(zip(parties.keys(), v)) for v in zip(*parties.values())]
        data['parties'] = parties
        return data


class DecisionSchema(CommonSchema):
    class Meta:
        model = Decision
        abbr = 'dec'
        type = 'decision'
        solr_filters = [
            'type_of_document', 'status', 'treaty_name',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'title_of_text', 'status', 'publish_date', 'update_date',
            'treaty_name', 'short_title',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,
            'short_title': 100,
            'summary': 50,
            'body': 20,
        })

    ID_FIELD = 'decNumber'
    KEYWORDS_FIELD = 'decKeyword'
    SUBJECTS_FIELD = 'docSubject'  # COP decisions don't have subjects (?)

    type_of_document = fields.String(load_from='decType')

    body = fields.String(load_from='decBody', multilingual=True)
    file_names = fields.List(fields.String(), load_from='decFileNames')
    file_urls = fields.List(fields.String(), load_from='decFileUrls')
    # TODO: check if this is deprecated
    decision_id = fields.String(load_from='decId')
    language = fields.List(fields.String(), load_from='decLanguage',
                           multilingual=True)
    url = fields.String(load_from='decLink')
    long_title = fields.String(load_from='decLongTitle', multilingual=True)
    meeting_id = fields.String(load_from='decMeetingId')
    meeting_title = fields.String(load_from='decMeetingTitle')
    meeting_url = fields.String(load_from='decMeetingUrl')
    publish_date = fields.Date(load_from='decPublishDate', missing=None)
    short_title = fields.String(load_from='decShortTitle', multilingual=True,
                                missing='')
    status = fields.String(load_from='decStatus')
    summary = fields.String(load_from='decSummary', multilingual=True)
    title_of_text = fields.List(fields.String(), load_from='decTitleOfText')
    treaty_slug = fields.String(load_from='decTreaty')
    treaty_id = fields.String(load_from='decTreatyId')
    treaty_name = fields.String(load_from='decTreatyName',
                                multilingual=True)
    update_date = fields.Date(load_from='decUpdateDate', missing=None)


class LiteratureSchema(CommonSchema):
    class Meta:
        model = Literature
        abbr = 'lit'
        type = 'literature'
        solr_filters = [
            'type_of_text', 'publisher', 'orig_serial_title', 'author',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'type_of_text',
            'long_title', 'long_title_other', 'paper_title_of_text',
            'paper_title_of_text_other', 'orig_serial_title',
            'title_of_text_short', 'title_of_text_short_other',
            'title_of_text_transl',
            'date_of_entry', 'date_of_modification',
            'date_of_text', 'date_of_text_ser',
            'abstract', 'abstract_other',
            'jurisdiction', # "scope"
            #'author',
            'author_a', 'author_m', 'corp_author_a', 'corp_author_m',
            'publisher', 'publication_place',
            'volume_no', 'collation', 'series_flag',
            'countries', 'region', 'language_of_document',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,
            'long_title_other': 100,

            'paper_title_of_text': 100,
            'paper_title_of_text_other': 100,

            'abstract': 50,
            'abstract_other': 50,

            'basin': 25,
            'region': 25,
        })


    ID_FIELD = 'litId'  # this is actually multivalued (?)
    KEYWORDS_FIELD = 'litKeyword'
    SUBJECTS_FIELD = 'litSubject'

    # TODO: False list (?)
    type_of_text = fields.List(fields.String(),
                               load_from='litTypeOfText',
                               multilingual=True)

    abstract = fields.String(load_from='litAbstract', multilingual=True)
    abstract_other = fields.String(load_from='litAbstract_other')
    available_in = fields.String(load_from='litAvailableIn')
    basin = fields.List(fields.String(), load_from='litBasin',
                        multilingual=True)
    call_no = fields.String(load_from='litCallNo')
    collation = fields.String(load_from='litCollation')
    conf_date = fields.String(load_from='litConfDate')
    conf_name = fields.String(load_from='litConfName', multilingual=True)
    conf_name_other = fields.String(load_from='litConfName_other')
    conf_no = fields.String(load_from='litConfNo')
    conf_place = fields.String(load_from='litConfPlace')
    contributor = fields.List(fields.String(), load_from='litContributor')
    countries = fields.List(fields.String(), load_from='litCountry',
                            multilingual=True)
    court_decision_reference = fields.List(
        fields.String(),
        load_from='litCourtDecisionReference')
    date_of_entry = fields.Date(load_from='litDateOfEntry')
    date_of_modification = fields.Date(load_from='litDateOfModification')
    date_of_text = fields.String(load_from='litDateOfText', missing=None)
    date_of_text_ser = fields.String(load_from='litDateOfTextSer', missing=None)
    display_details = fields.String(load_from='litDisplayDetails')
    display_region = fields.String(load_from='litDisplayRegion',
                                   multilingual=True)
    display_title = fields.String(load_from='litDisplayTitle')
    display_type = fields.String(load_from='litDisplayType', multilingual=True)
    eu_legislation_reference = fields.List(
        fields.String(),
        load_from='litEULegislationReference')
    edition = fields.String(load_from='litEdition')
    faolex_reference = fields.List(fields.String(),
                                   load_from='litFaolexReference')
    former_title = fields.String(load_from='litFormerTitle')
    frequency = fields.String(load_from='litFrequency')
    holdings = fields.String(load_from='litHoldings')
    isbn = fields.String(load_from='litISBN')
    issn = fields.String(load_from='litISSN')
    id2 = fields.List(fields.String(), load_from='litId2')
    int_org = fields.String(load_from='litIntOrg', multilingual=True)
    internet_reference = fields.String(load_from='litInternetReference')
    language_of_document = fields.List(fields.String(),
                                       load_from='litLanguageOfDocument',
                                       multilingual=True)
    language_of_translation = fields.String(
        load_from='litLanguageOfTranslation',
        multilingual=True)
    link_doi = fields.String(load_from='litLinkDOI')
    link_to_abstract = fields.String(load_from='litLinkToAbstract')
    link_to_full_text = fields.List(fields.String(),
                                    load_from='litLinkToFullText')
    literature_reference = fields.List(fields.String(),
                                       load_from='litLiteratureReference')
    location = fields.String(load_from='litLocation')
    long_title = fields.String(load_from='litLongTitle', multilingual=True,
                               missing='')
    long_title_other = fields.String(load_from='litLongTitle_other')
    mode_of_acquisition = fields.String(load_from='litModeOfAcquisition')
    national_legislation_reference = fields.List(
        fields.String(),
        load_from='litNationalLegislationReference')
    paper_title_of_text = fields.String(load_from='litPaperTitleOfText',
                                        multilingual=True, missing='')
    paper_title_of_text_other = fields.String(
        load_from='litPaperTitleOfText_other')
    publication_place = fields.String(load_from='litPublPlace')
    publisher = fields.String(load_from='litPublisher')
    region = fields.List(fields.String(), load_from='litRegion',
                         multilingual=True)
    related_monograph = fields.String(load_from='litRelatedMonograph')
    related_web_site = fields.String(load_from='litRelatedWebSite')
    jurisdiction = fields.String(load_from='litScope', multilingual=True)
    search_date = fields.String(load_from='litSearchDate')
    serial_status = fields.String(load_from='litSerialStatus')
    orig_serial_title = fields.String(load_from='litSerialTitle',
                                      missing='')
    series_flag = fields.String(load_from='litSeriesFlag')
    territorial_subdivision = fields.String(
        load_from='litTerritorialSubdivision',
        multilingual=True)
    title_abbreviation = fields.String(load_from='litTitleAbbreviation')
    title_of_text_short = fields.String(load_from='litTitleOfTextShort',
                                        multilingual=True, missing='')
    title_of_text_short_other = fields.String(
        load_from='litTitleOfTextShort_other')
    title_of_text_transl = fields.String(load_from='litTitleOfTextTransl',
                                         multilingual=True, missing='')
    treaty_reference = fields.List(fields.String(),
                                   load_from='litTreatyReference')
    volume_no = fields.String(load_from='litVolumeNo', missing='')

    # Authors
    author = fields.List(fields.String(),
                         load_from='litAuthor',
                         missing=[])
    author_a = fields.List(fields.String(), load_from='litAuthorA', missing=[])
    author_m = fields.List(fields.String(), load_from='litAuthorM', missing=[])
    corp_author_a = fields.List(fields.String(), load_from='litCorpAuthorA',
                                missing=[])
    corp_author_m = fields.List(fields.String(), load_from='litCorpAuthorM',
                                missing=[])


class CourtDecisionSchema(CommonSchema):
    class Meta:
        model = CourtDecision
        abbr = 'cd'
        type = 'court_decision'
        solr_filters = [
            'type_of_document', 'territorial_subdivision',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'title_of_text', 'type_of_document', 'country', 'date_of_text',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'title_of_text': 100,
            'abstract': 50,
            'region': 25,
        })

    ID_FIELD = 'cdLeoId'
    KEYWORDS_FIELD = 'cdKeyword'
    SUBJECTS_FIELD = 'cdSubject'

    # TODO: Multivalued ?
    type_of_document = fields.String(load_from='cdTypeOfText')

    # TODO: this is common to more. group together?
    abstract = fields.String(load_from='cdAbstract', multilingual=True)
    country = fields.String(load_from='cdCountry', multilingual=True)

    court_name = fields.String(load_from='cdCourtName')
    date_of_entry = fields.Date(load_from='cdDateOfEntry')
    date_of_modification = fields.Date(load_from='cdDateOfModification')
    date_of_text = fields.Date(load_from='cdDateOfText', missing=None)
    files = fields.List(fields.String(), load_from='cdFiles')
    internet_reference = fields.String(load_from='cdInternetReference',
                                       multilingual=True)
    jurisdiction = fields.String(load_from='cdJurisdiction')
    justices = fields.List(fields.String(), load_from='cdJustices')
    language_of_document = fields.List(fields.String(),
                                       load_from='cdLanguageOfDocument',
                                       multilingual=True)
    link_to_full_text = fields.String(load_from='cdLinkToFullText',
                                      multilingual=True)
    original_id = fields.String(load_from='cdOriginalId')
    reference_number = fields.String(load_from='cdReferenceNumber')
    seat_of_court = fields.String(load_from='cdSeatOfCourt', multilingual=True)
    status_of_decision = fields.String(load_from='cdStatusOfDecision')
    territorial_subdivision = fields.String(load_from='cdTerritorialSubdivision',
                                            multilingual=True)
    title_of_text = fields.String(load_from='cdTitleOfText', multilingual=True,
                                  missing='')
    treaty_reference = fields.List(fields.String(),
                                   load_from='cdTreatyReference')
    region = fields.List(fields.String(), load_from='cdRegion',
                         multilingual=True)


class LegislationSchema(CommonSchema):
    class Meta:
        model = Legislation
        abbr = 'leg'
        type = 'legislation'
        solr_filters = [
            'type_of_document', 'territorial_subdivision',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'short_title', 'long_title', 'country',
            'date', 'consolidation_date', # "year" / "original year"
            'status', 'territorial_subdivision',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,
            'short_title': 100,

            'basin': 25,
            'region': 25,
        })

    ID_FIELD = 'legId'
    KEYWORDS_FIELD = 'legKeyword'
    SUBJECTS_FIELD = 'legSubject'

    type_of_document = fields.String(load_from='legType',
                                     multilingual=True)
    short_title = fields.String(load_from='legTitle', missing='')
    long_title = fields.String(load_from='legLongTitle', missing='')

    abstract = fields.String(load_from='legAbstract')
    country = fields.String(load_from='legCountry', multilingual=True)
    country_iso = fields.String(load_from='legCountry_iso')
    entry_date = fields.Date(load_from='legEntryDate')
    entry_into_force = fields.String(load_from='legEntryIntoForce')
    region = fields.List(fields.String(), load_from='legGeoArea',
                         multilingual=True)
    basin = fields.List(fields.String(), load_from='legBasin',
                        multilingual=True)
    keyword_code = fields.List(fields.String(), load_from='legKeyword_code')
    language_code = fields.List(fields.String(), load_from='legLanguage_code')
    language = fields.List(fields.String(), load_from='legLanguage',
                           multilingual=True)
    link_to_full_text = fields.String(load_from='legLinkToFullText')
    modification_date = fields.Date(load_from='legModificationDate')
    related_web_site = fields.String(load_from='legRelatedWebSite')
    search_date = fields.Date(load_from='legSearchDate')
    source = fields.String(load_from='legSource')
    status = fields.String(load_from='legStatus')
    subject_code = fields.List(fields.String(), load_from='legSubject_code')
    territorial_subdivision = fields.String(load_from='legTerritorialSubdivision')
    type_code = fields.String(load_from='legTypeCode')
    date = fields.String(load_from='legYear')
    consolidation_date = fields.String(load_from='legOriginalYear')

    # References
    amends = fields.List(fields.String(), load_from='legAmends')
    implements = fields.List(fields.String(), load_from='legImplement')
    repeals = fields.List(fields.String(), load_from='legRepeals')


class __FieldProperties(object):
    __slots__ = (
        'type', 'name', 'load_from', 'multilingual', 'multivalue', 'datatype',
        'solr_filter', 'solr_fetch', 'solr_boost', 'solr_highlight',
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_source_field(self, lang):
        if not self.multilingual:
            return self.load_from
        else:
            return "%s_%s" % (self.load_from, lang)

    def __repr__(self):
        props = []
        for prop in 'multilingual', 'multivalue':
            if getattr(self, prop):
                props.append(prop)
        return "< {}.{} ({}) : {}) >".format(
            self.type, self.name, self.load_from, ', '.join(props))


def __get_field_properties(base_schema, *schemas):
    props = defaultdict(OrderedDict)

    for schema in (base_schema, ) + schemas:
        if schema is base_schema:
            typ = '_'
        else:
            typ = schema.opts.type

        for name, field in schema().declared_fields.items():
            # don't duplicate inherited fields
            if (schema != base_schema and
                name in props['_'] and
                (base_schema._declared_fields.get(name) is
                 schema._declared_fields.get(name))
            ):
                continue

            fp = __FieldProperties()
            fp.type = typ
            fp.name = name
            fp.load_from = field.load_from
            fp.multilingual = field.multilingual
            multivalue = isinstance(field, fields.List)
            fp.multivalue = multivalue
            if multivalue:
                inst = field.container
            else:
                inst = field
            fp.datatype = inst.__class__.__name__.lower()

            fp.solr_filter = name in schema.opts.solr_filters
            for prop in ('solr_fetch', 'solr_highlight'):
                setattr(fp, prop, name in getattr(schema.opts, prop))
            try:
                fp.solr_boost = schema.opts.solr_boost[name]
            except KeyError:
                fp.solr_boost = None

            props[typ][field.canonical_name] = fp

    return props


__FPROPS = __get_field_properties(
    BaseSchema,
    TreatySchema,
    DecisionSchema,
    LegislationSchema,
    CourtDecisionSchema,
    LiteratureSchema
)

FIELD_MAP = {
    k: v.keys() for k, v in __FPROPS.items()
}

FILTER_FIELDS = OrderedDict(
    (k, p) for _fps in __FPROPS.values() for k, p in _fps.items()
    if p.solr_filter
)

FETCH_FIELDS = OrderedDict(
    (k, p) for _fps in __FPROPS.values() for k, p in _fps.items()
    if p.solr_fetch
)

BOOST_FIELDS = OrderedDict(
    (k, p) for _fps in __FPROPS.values() for k, p in _fps.items()
    if p.solr_boost
)

import pprint
#pprint.pprint(FILTER_FIELDS, indent=2, width=200)
#pprint.pprint(FETCH_FIELDS, indent=2, width=200)
#pprint.pprint(dict(BOOST_FIELDS), indent=2, width=200)
