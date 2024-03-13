"""
Usage:

>>> lschema = schema.LegislationSchema()
>>> lschema.context={'language': 'fr'}
>>> result, errors = lschema.load({'id': 'abc', 'legCountry_fr': 'xyz'})
>>> result
{'country': 'xyz', 'id': 'abc'}

"""

import logging

from collections import OrderedDict
from django.conf import settings
from marshmallow import post_load, pre_load

from ecolex.lib.schema import Schema, fields, get_field_properties
from ecolex.solr_models_re import (
    CourtDecision, Decision, Legislation, Literature, Treaty, TreatyParty,
)


logger = logging.getLogger(__name__)


class BaseSchema(Schema):
    """
    Inherited by all main object schemas.
    """

    id = fields.String()
    slug = fields.String()
    type = fields.String()
    indexed_at = fields.DateTime(load_from='indexedDate', missing=None)
    updated_at = fields.DateTime(load_from='updatedDate', missing=None)

    text = fields.List(fields.String())

    # common fields, used for filtering / faceting
    # TODO: redundant with CommonSchema below?
    xkeywords = fields.List(fields.String(),
                            load_from='docKeyword',
                            multilingual=True)
    xsubjects = fields.List(fields.String(),
                            load_from='docSubject',
                            multilingual=True)
    xcountry = fields.List(fields.String(),
                           load_from='docCountry',
                           multilingual=True)
    xregion = fields.List(fields.String(),
                          load_from='docRegion',
                          multilingual=True)
    xlanguage = fields.List(fields.String(),
                            load_from='docLanguage',
                            multilingual=True)

    xdate = fields.Date(load_from='docDate')
    xentrydate = fields.Date(load_from='docEntryDate')

    class Meta:
        solr_filters = [
            'type', 'xkeywords', 'xsubjects', 'xcountry', 'xregion',
            'xlanguage', 'xdate',
        ]
        solr_facets = [f for f in solr_filters if f != 'xdate']
        # TODO Move indexed_at, updated_at to query fetch_fields (used only for
        # sitemap.xml)
        solr_fetch = ['id', 'slug', 'type', 'indexed_at', 'updated_at']
        solr_boost = {
            'text': 20,
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


class TranslationSchema(Schema):
    language = fields.String(load_from='language')
    value = fields.String(load_from='value')


class TranslationListSchema(Schema):
    language = fields.String(load_from='language')
    value = fields.List(fields.String(), load_from='value')


class TreatyPartySchema(Schema):
    country = fields.String(load_from='partyCountry', multilingual=True)
    country_en = fields.String(load_from='partyCountry_en')
    acceptance_approval = fields.Date(load_from='partyDateOfAcceptanceApproval')
    accession_approbation = fields.Date(
        load_from='partyDateOfAccessionApprobation')
    consent_to_be_bound = fields.Date(load_from='partyDateOfConsentToBeBound')
    definite_signature = fields.Date(load_from='partyDateOfDefiniteSignature')
    entry_into_force = fields.Date(load_from='partyEntryIntoForce',
                                   missing=None)
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
            'title_of_text_short', 'title_abbreviation', 'type_of_document',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'title_of_text': 110,
            'title_abbreviation': 75,
            'title_of_text_short': 75,
            'abstract': 50,
            'basin': 25,
            'region': 25,
        })
        solr_highlight = [
            'title_of_text', 'title_of_text_short',# 'abstract'
        ]

    type_of_document = fields.String(load_from='trTypeOfText',
                                     multilingual=True)

    parties = fields.Nested(TreatyPartySchema, many=True)
    title_translations = fields.Nested(TranslationSchema, many=True)
    link_translations = fields.Nested(TranslationListSchema, many=True)

    abstract = fields.List(fields.String(), load_from='trAbstract',
                           multilingual=True)
    author = fields.List(fields.String(), load_from='trAuthor')
    author_a = fields.List(fields.String(), load_from='trAuthorA')
    author_m = fields.List(fields.String(), load_from='trAuthorM')
    author_whole = fields.List(fields.String(), load_from='trAuthorWhole')

    available_in = fields.String(load_from='trAvailableIn')

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

    informea_id = fields.String(load_from='trInformeaId',
                                missing=None)
    internet_reference = fields.List(fields.String(),
                                     load_from='trInternetReference',
                                     multilingual=True)
    into_force_treaty = fields.List(fields.String(),
                                    load_from='trIntoForceTreaty')
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
    logo_medium = fields.String(load_from='trLogoMedium')
    number_of_pages = fields.List(fields.String(), load_from='trNumberOfPages')
    number_of_parties = fields.List(fields.String(),
                                    load_from='trNumberOfParties')
    official_publication = fields.List(fields.String(),
                                       load_from='trOfficialPublication')
    order = fields.String(load_from='trOrder')
    title_of_text = fields.String(load_from='trTitleOfText',
                                  multilingual=True,
                                  missing='')
    parent_id = fields.Integer(load_from='trParentId')
    place_of_adoption = fields.String(load_from='trPlaceOfAdoption')
    primary = fields.List(fields.String(), load_from='trPrimary')
    region = fields.List(fields.String(), load_from='trRegion',
                         multilingual=True)
    relevant_text_treaty = fields.List(fields.String(),
                                       load_from='trRelevantTextTreaty')
    search_date = fields.Date(load_from='trSearchDate')
    seat_of_court = fields.List(fields.String(), load_from='trSeatOfCourt')
    status = fields.String(load_from='trStatus')
    theme_secondary = fields.List(fields.String(), load_from='trThemeSecondary')
    title_abbreviation = fields.List(fields.String(),
                                     load_from='trTitleAbbreviation',
                                     missing=[])
    title_of_text_short = fields.String(load_from='trTitleOfTextShort',
                                        missing='')
    related_web_site = fields.List(fields.String(), load_from='trRelatedWebSite')
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

    @pre_load
    def handle_translations(self, data):
        data['title_translations'] = extract_translations(
            data, 'trTitleOfText')
        data['link_translations'] = extract_translations(
            data, 'trLinkToFullText')
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
            'treaty_name', 'short_title', 'treaty_id', 'treaty_slug',
            'meeting_id', 'meeting_title',
            'dec_number', 'decId'
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,
            'short_title': 100,
            'summary': 50,
            'abstract': 20,
        })
        solr_highlight = [
            'short_title',  # 'body',
        ]

    ID_FIELD = 'decId'
    KEYWORDS_FIELD = 'decKeyword'
    SUBJECTS_FIELD = 'docSubject'  # COP decisions don't have subjects (?)

    dec_number = fields.String(load_from='decNumber')
    type_of_document = fields.String(load_from='decType')

    abstract = fields.String(load_from='decBody', multilingual=True)
    file_names = fields.List(fields.String(), load_from='decFileNames',
                             missing=[])
    file_urls = fields.List(fields.String(), load_from='decFileUrls',
                            missing=[])
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
    treaty_id = fields.String(load_from='decTreatyId', missing=None)
    treaty_name = fields.String(load_from='decTreatyName',
                                multilingual=True)
    update_date = fields.Date(load_from='decUpdateDate', missing=None)

    # these fields are used temporarily for grouping / ordering,
    # and they should be removed after a full re-index.
    _meeting_id = fields.String(load_from='decMeetingId_group')
    _meeting_number = fields.String(load_from='decNumber_sort')


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
            'long_title', 'paper_title_of_text',
            'orig_serial_title', 'year_of_text',
            'date_of_entry', 'date_of_modification',
            'date_of_text', 'date_of_text_ser',
            'abstract',
            'jurisdiction',  # "scope"
            # 'author',
            'author_a', 'author_m', 'corp_author_a', 'corp_author_m',
            'publisher', 'publication_place',
            'volume_no', 'collation', 'series_flag',
            'countries', 'region', 'language_of_document',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,

            'paper_title_of_text': 100,

            'abstract': 50,

            'basin': 25,
            'region': 25,
        })
        solr_highlight = [
            'paper_title_of_text', 'long_title', 'abstract',
        ]

    ID_FIELD = 'litId'  # this is actually multivalued (?)
    KEYWORDS_FIELD = 'litKeyword'
    SUBJECTS_FIELD = 'litSubject'

    type_of_text = fields.List(fields.String(),
                               load_from='litTypeOfText',
                               multilingual=True)

    title_translations = fields.Nested(TranslationSchema, many=True)

    abstract = fields.String(load_from='litAbstract', multilingual=True)
    available_in = fields.String(load_from='litAvailableIn')
    basin = fields.List(fields.String(), load_from='litBasin',
                        multilingual=True)
    call_no = fields.String(load_from='litCallNo')
    collation = fields.String(load_from='litCollation')
    conf_date = fields.String(load_from='litConfDate', missing='')
    conf_name = fields.String(load_from='litConfName', multilingual=True,
                              missing='')
    conf_no = fields.String(load_from='litConfNo', missing='')
    conf_place = fields.String(load_from='litConfPlace', missing='')
    contributor = fields.List(fields.String(), load_from='litContributor')
    countries = fields.List(fields.String(), load_from='litCountry',
                            multilingual=True)
    court_decision_reference = fields.List(
        fields.String(),
        load_from='litCourtDecisionReference',
        missing=[])
    court_decision_reference_informea = fields.List(
        fields.String(),
        load_from='litCourtDecisionReference2',
        missing=[])
    date_of_entry = fields.Date(load_from='litDateOfEntry')
    date_of_modification = fields.Date(load_from='litDateOfModification')
    date_of_text = fields.String(load_from='litDateOfText', missing=None)
    year_of_text = fields.String(load_from='litYearOfText', missing=None)
    date_of_text_ser = fields.String(load_from='litDateOfTextSer', missing=None)
    lit_date = fields.Date(load_from='litDate', missing=None)
    display_details = fields.String(load_from='litDisplayDetails')
    display_region = fields.String(load_from='litDisplayRegion',
                                   multilingual=True)
    display_title = fields.String(load_from='litDisplayTitle')
    display_type = fields.String(load_from='litDisplayType', multilingual=True)
    eu_legislation_reference = fields.List(
        fields.String(), load_from='litEULegislationReference', missing=[])
    edition = fields.String(load_from='litEdition')
    faolex_reference = fields.List(fields.String(),
                                   load_from='litFaolexReference',
                                   missing=[])
    former_title = fields.String(load_from='litFormerTitle')
    frequency = fields.String(load_from='litFrequency')
    holdings = fields.String(load_from='litHoldings')
    isbn = fields.List(fields.String(), load_from='litISBN')
    issn = fields.String(load_from='litISSN')
    id2 = fields.List(fields.String(), load_from='litId2')
    reference_number = fields.String(load_from='litOtherDocId')
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
    reference = fields.List(fields.String(),
                            load_from='litLiteratureReference',
                            missing=[])
    location = fields.String(load_from='litLocation')
    long_title = fields.String(load_from='litLongTitle', multilingual=True,
                               missing='')
    mode_of_acquisition = fields.String(load_from='litModeOfAcquisition')
    national_legislation_reference = fields.List(
        fields.String(), load_from='litNationalLegislationReference',
        missing=[])
    paper_title_of_text = fields.String(load_from='litPaperTitleOfText',
                                        multilingual=True, missing='')
    publication_place = fields.String(load_from='litPublPlace')
    publisher = fields.String(load_from='litPublisher')
    region = fields.List(fields.String(), load_from='litRegion',
                         multilingual=True)
    related_monograph = fields.String(load_from='litRelatedMonograph',
                                      missing=None)
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
    title_of_text_transl = fields.String(load_from='litTitleOfTextTransl',
                                         multilingual=True, missing='')
    treaty_reference = fields.List(fields.String(),
                                   load_from='litTreatyReference',
                                   missing=[])
    cop_decision_reference = fields.List(fields.String(),
                                         load_from='litCopDecisionReference',
                                         missing=[])
    chapter = fields.List(fields.String(),
                          load_from='litChapterReference',
                          missing=[])
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

    @pre_load
    def handle_translations(self, data):
        id = data['litId']
        if id.startswith('MON'):
            title_field = 'litLongTitle'
        elif id.startswith('ANA'):
            title_field = 'litPaperTitleOfText'
        else:
            return data

        data['title_translations'] = extract_translations(data, title_field)
        return data


class CourtDecisionSchema(CommonSchema):
    class Meta:
        model = CourtDecision
        abbr = 'cd'
        type = 'court_decision'
        solr_filters = [
            'type_of_document', 'territorial_subdivision',
        ]
        solr_fetch = CommonSchema.Meta.solr_fetch + [
            'title_of_text', 'type_of_document', 'country', 'date_of_text', 'leo_english_url'
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'title_of_text': 100,
            'abstract': 50,
            'region': 25,
        })
        solr_highlight = [
            'title_of_text', #'abstract',
        ]

    ID_FIELD = 'cdOriginalId'
    KEYWORDS_FIELD = 'cdKeyword'
    SUBJECTS_FIELD = 'cdSubject'

    # TODO: Multivalued ?
    type_of_document = fields.String(load_from='cdTypeOfText')

    # TODO: this is common to more. group together?
    abstract = fields.String(load_from='cdAbstract', multilingual=True)
    link_to_abstract = fields.String(load_from='cdLinkToAbstract')
    country = fields.List(fields.String(), load_from='cdCountry',
                          multilingual=True)

    court_name = fields.String(load_from='cdCourtName')
    date_of_entry = fields.Date(load_from='cdDateOfEntry')
    date_of_modification = fields.Date(load_from='cdDateOfModification')
    date_of_text = fields.Date(load_from='cdDateOfText', missing=None)
    files = fields.List(fields.String(), load_from='cdFiles')
    available_in = fields.String(load_from='cdAvailableIn')

    jurisdiction = fields.String(load_from='cdJurisdiction')
    justices = fields.List(fields.String(), load_from='cdJustices')
    language_of_document = fields.List(fields.String(),
                                       load_from='cdLanguageOfDocument',
                                       multilingual=True)
    leo_english_url = fields.String(load_from='cdLeoEnglishUrl')
    leo_id = fields.String(load_from='cdLeoId')
    link_to_full_text = fields.List(fields.String(),
                                    load_from='cdLinkToFullText')
    related_web_site = fields.String(load_from='cdRelatedUrl_en', missing=None)
    original_id = fields.String(load_from='cdOriginalId')
    reference_number = fields.String(load_from='cdReferenceNumber')
    seat_of_court = fields.String(load_from='cdSeatOfCourt', multilingual=True)
    status_of_decision = fields.String(load_from='cdStatusOfDecision')
    territorial_subdivision = fields.String(
        load_from='cdTerritorialSubdivision', multilingual=True)
    title_of_text = fields.String(load_from='cdTitleOfText', multilingual=True,
                                  missing='')
    treaty_reference = fields.List(fields.String(),
                                   load_from='cdTreatyReference', missing=None)
    legislation_reference = fields.List(fields.String(),
                                        load_from='cdFaolexReference',
                                        missing=None)
    region = fields.List(fields.String(), load_from='cdRegion',
                         multilingual=True)
    cites = fields.List(fields.String(), load_from='cdCourtDecisionReference',
                        missing=None)


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
            'year', 'original_year',  # "year" / "original year"
            'source',
            'status', 'territorial_subdivision',
        ]
        solr_boost = dict(CommonSchema.Meta.solr_boost, **{
            'long_title': 100,
            'short_title': 100,
            'abstract': 50,
            'basin': 25,
            'region': 25,
        })
        solr_highlight = [
            'short_title', 'long_title', #'abstract',
        ]

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
    related_web_site = fields.String(load_from='legRelatedWebSite')
    source = fields.String(load_from='legSource')
    status = fields.String(load_from='legStatus')
    subject_code = fields.List(fields.String(), load_from='legSubject_code')
    territorial_subdivision = fields.String(
        load_from='legTerritorialSubdivision')
    type_code = fields.String(load_from='legTypeCode')
    year = fields.String(load_from='legYear')
    date = fields.Date(load_from='legDate', missing=None)
    original_year = fields.String(load_from='legOriginalYear')

    # References
    amends = fields.List(fields.String(), load_from='legAmends')
    implements = fields.List(fields.String(), load_from='legImplement')
    repeals = fields.List(fields.String(), load_from='legRepeals')

    treaty_implements = fields.List(fields.String(),
                                    load_from='legImplementTreaty', missing=None)
    treaty_cites = fields.List(fields.String(),
                               load_from='legCitesTreaty', missing=None)


__OBJECT_SCHEMAS = (
    TreatySchema,
    DecisionSchema,
    LegislationSchema,
    CourtDecisionSchema,
    LiteratureSchema,
)

SCHEMA_MAP = {
    schema.opts.type: schema()
    for schema in __OBJECT_SCHEMAS
}


def to_object(data, language):
    typ = data['type']
    schema = SCHEMA_MAP[typ]
    result, errors = schema.load(data, language=language)
    if errors:
        raise ValueError(errors)
    return result


FIELD_PROPERTIES = get_field_properties(
    BaseSchema, __OBJECT_SCHEMAS
)

FIELD_MAP = OrderedDict(
    (k, v.keys()) for k, v in FIELD_PROPERTIES.items()
)

FILTER_FIELDS = OrderedDict(
    (k, p) for _fps in FIELD_PROPERTIES.values() for k, p in _fps.items()
    if p.solr_filter
)

FACET_FIELDS = OrderedDict(
    (k, p) for _fps in FIELD_PROPERTIES.values() for k, p in _fps.items()
    if p.solr_facet
)

# build stats for all filters that are date(/time)s or numbers
STATS_FIELDS = OrderedDict(
    (k, p) for k, p in FILTER_FIELDS.items()
    if p.datatype in (
            'number', 'integer', 'decimal', 'float',
            'datetime', 'localdatetime', 'time', 'date',
    )
)

FETCH_FIELDS = OrderedDict(
    (k, p) for _fps in FIELD_PROPERTIES.values() for k, p in _fps.items()
    if p.solr_fetch
)

BOOST_FIELDS = OrderedDict(
    (k, p) for _fps in FIELD_PROPERTIES.values() for k, p in _fps.items()
    if p.solr_boost
)

HIGHLIGHT_FIELDS = OrderedDict(
    (k, p) for _fps in FIELD_PROPERTIES.values() for k, p in _fps.items()
    if p.solr_highlight
)

# hardcode the sort field. 'cause practicality...
SORT_FIELD = FIELD_PROPERTIES['_']['xdate']
SORT_FIELD_FALLBACK = FIELD_PROPERTIES['_']['xentrydate']

def extract_translations(data, field_name):
    translations = [{'language': k.split('_')[-1], 'value': v}
                    for k, v in data.items()
                    if k.startswith('%s_'%(field_name,))]
    # make sure the order of languages is the same as settings.LANGUAGE_MAP
    return sorted(
        translations,
        key = lambda x: list(settings.LANGUAGE_MAP.keys()).index(x['language'])
    )
