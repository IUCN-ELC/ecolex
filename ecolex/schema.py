"""
Usage:

>>> lschema = schema.LegislationSchema()
>>> lschema.context={'language': 'fr'}
>>> result, errors = lschema.load({'id': 'abc', 'legCountry_fr': 'xyz'})
>>> result
{'country': 'xyz', 'id': 'abc'}

"""


from ecolex.lib.schema import Schema, fields


class BaseSchema(Schema):
    """
    Inherited by all main object schemas.
    """

    id = fields.String()
    type = fields.String()
    source = fields.String()
    indexed_at = fields.DateTime(load_from='indexedDate')
    updated_at = fields.DateTime(load_from='updatedDate')

    # Common fields that have different names in Solr
    document_id = fields.String(load_from_attribute='ID_FIELD')
    keywords = fields.List(fields.String(), multilingual=True,
                           load_from_attribute='KEYWORDS_FIELD')
    subjects = fields.List(fields.String(), multilingual=True,
                           load_from_attribute='SUBJECTS_FIELD')


class TreatyPartySchema(Schema):
    country = fields.String(load_from='partyCountry')
    acceptance_approval_date = fields.Date(
        load_from='partyDateOfAcceptanceApproval')
    accession_approbation_date = fields.Date(
        load_from='partyDateOfAccessionApprobation')
    consent_to_be_bound_date = fields.Date(
        load_from='partyDateOfConsentToBeBound')
    definite_signature_date = fields.Date(
        load_from='partyDateOfDefiniteSignature')
    participation_date = fields.Date(
        load_from='partyDateOfParticipation')
    provisional_application_date = fields.Date(
        load_from='partyDateOfProvisionalApplication')
    ratification_date = fields.Date(
        load_from='partyDateOfRatification')
    reservation_date = fields.Date(
        load_from='partyDateOfReservation')
    simple_signature_date = fields.Date(
        load_from='partyDateOfSimpleSignature')
    succession_date = fields.Date(
        load_from='partyDateOfSuccession')
    withdrawal_date = fields.Date(
        load_from='partyDateOfWithdrawal')
    entry_into_force_date = fields.Date(
        load_from='partyEntryIntoForce')


class TreatySchema(BaseSchema):
    ID_FIELD = 'trElisId'
    KEYWORDS_FIELD = 'trKeyword'
    SUBJECTS_FIELD = 'trSubject'

    type_of_document = fields.List(fields.String(), load_from='trTypeOfText',
                                   multilingual=True)  # False list (?)

    # setting these requires special handling, TODO
    parties = fields.Nested(TreatyPartySchema,
                            many=True)
    abstract = fields.List(fields.String(), load_from='trAbstract',
                           multilingual=True)
    amended_by = fields.List(fields.String(), load_from='trAmendedBy')
    amends_treaty = fields.List(fields.String(), load_from='trAmendsTreaty')
    author = fields.List(fields.String(), load_from='trAuthor')
    author_a = fields.List(fields.String(), load_from='trAuthorA')
    author_m = fields.List(fields.String(), load_from='trAuthorM')
    author_whole = fields.List(fields.String(), load_from='trAuthorWhole')
    available_in = fields.List(fields.String(), load_from='trAvailableIn')  # False list
    basin = fields.List(fields.String(), load_from='trBasin', multilingual=True)
    cited_by = fields.List(fields.String(), load_from='trCitedBy')
    cites_treaty = fields.List(fields.String(), load_from='trCitesTreaty')
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
    depository = fields.List(fields.String(), load_from='trDepository',
                             multilingual=True)
    enabled = fields.String(load_from='trEnabled')
    enabled_by_treaty = fields.List(fields.String(),
                                    load_from='trEnabledByTreaty')
    enables_treaty = fields.List(fields.String(), load_from='trEnablesTreaty')
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
    place_of_adoption = fields.List(fields.String(),
                                    load_from='trPlaceOfAdoption')  # False list
    primary = fields.List(fields.String(), load_from='trPrimary')
    reference_to_literature = fields.List(fields.String(),
                                          load_from='trReferenceToLiterature')
    reference_to_treaties = fields.List(fields.String(),
                                        load_from='trReferenceToTreaties')
    region = fields.List(fields.String(), load_from='trRegion',
                         multilingual=True)
    relevant_text_treaty = fields.List(fields.String(),
                                       load_from='trRelevantTextTreaty')
    scope = fields.List(fields.String(), load_from='trScope')
    search_date = fields.Date(load_from='trSearchDate')
    seat_of_court = fields.List(fields.String(), load_from='trSeatOfCourt')
    status = fields.String(load_from='trStatus')
    superseded_by = fields.List(fields.String(), load_from='trSupersededBy')
    supersedes_treaty = fields.List(fields.String(),
                                    load_from='trSupersedesTreaty')
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


class DecisionSchema(BaseSchema):
    ID_FIELD = 'decNumber'
    KEYWORDS_FIELD = 'decKeyword'
    SUBJECTS_FIELD = 'docSubject'  # COP decisions don't have subjects (?)

    type_of_document = fields.String(load_from='decType')

    body = fields.String(load_from='decBody', multilingual=True)
    file_names = fields.List(fields.String(), load_from='decFileNames')
    file_urls = fields.List(fields.String(), load_from='decFileUrls')
    # TODO: check if this is deprecated
    decison_id = fields.String(load_from='decId')
    language = fields.List(fields.String(), load_from='decLanguage',
                           multilingual=True)
    link = fields.String(load_from='decLink')
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
    treaty = fields.String(load_from='decTreaty')
    treaty_id = fields.String(load_from='decTreatyId')
    treaty_name = fields.String(load_from='decTreatyName', multilingual=True)
    update_date = fields.Date(load_from='decUpdateDate', missing=None)


class LiteratureSchema(BaseSchema):
    ID_FIELD = 'litId'  # this is actually multivalued (?)
    KEYWORDS_FIELD = 'litKeyword'
    SUBJECTS_FIELD = 'litSubject'

    type_of_text = fields.List(fields.String(), load_from='litTypeOfText',
                               multilingual=True)  # False list (?)

    abstract = fields.String(load_from='litAbstract', multilingual=True)
    abstract_other = fields.String(load_from='litAbstract_other')
    author = fields.List(fields.String(), load_from='litAuthor', missing=[])
    author_article = fields.List(fields.String(), load_from='litAuthorArticle',
                                 missing=[])
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
    corp_author = fields.List(fields.String(), load_from='litCorpAuthor',
                              missing=[])
    corp_author_article = fields.List(fields.String(),
                                      load_from='litCorpAuthorArticle',
                                      missing=[])
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
    language_of_document = fields.String(load_from='litLanguageOfDocument',
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
    serial_title = fields.String(load_from='litSerialTitle', missing='')
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
    volume_no = fields.String(load_from='litVolumeNo')


class CourtDecisionSchema(BaseSchema):
    ID_FIELD = 'cdLeoId'
    KEYWORDS_FIELD = 'cdKeyword'
    SUBJECTS_FIELD = 'cdSubject'

    type_of_document = fields.String(load_from='cdTypeOfText')  # Multivalued ?

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
    territorial_subdivision = fields.String(
        load_from='cdTerritorialSubdivision',
        multilingual=True)
    title_of_text = fields.String(load_from='cdTitleOfText', multilingual=True,
                                  missing='')
    treaty_reference = fields.List(fields.String(),
                                   load_from='cdTreatyReference')


class LegislationSchema(BaseSchema):
    ID_FIELD = 'legId'
    KEYWORDS_FIELD = 'legKeyword'
    SUBJECTS_FIELD = 'legSubject'

    type_of_document = fields.String(load_from='legType', multilingual=True)
    short_title = fields.String(load_from='legTitle', missing='')
    long_title = fields.String(load_from='legLongTitle', missing='')

    abstract = fields.String(load_from='legAbstract')
    amends = fields.List(fields.String(), load_from='legAmends')
    consolidation_date = fields.Date(load_from='legConsolidationDate')
    country = fields.String(load_from='legCountry', multilingual=True)
    country_iso = fields.String(load_from='legCountry_iso')
    date = fields.Date(load_from='legDate')
    entry_date = fields.Date(load_from='legEntryDate')
    entry_into_force = fields.String(load_from='legEntryIntoForce')
    geo_area = fields.List(fields.String(), load_from='legGeoArea',
                           multilingual=True)
    implement = fields.List(fields.String(), load_from='legImplement')
    keyword_code = fields.List(fields.String(), load_from='legKeyword_code')
    language_code = fields.List(fields.String(), load_from='legLanguage_code')
    language = fields.List(fields.String(), load_from='legLanguage',
                           multilingual=True)
    link_to_full_text = fields.String(load_from='legLinkToFullText')
    modification_date = fields.Date(load_from='legModificationDate')
    original_date = fields.Date(load_from='legOriginalDate')
    related_web_site = fields.String(load_from='legRelatedWebSite')
    repeals = fields.List(fields.String(), load_from='legRepeals')
    search_date = fields.Date(load_from='legSearchDate')
    source = fields.String(load_from='legSource')
    status = fields.String(load_from='legStatus')
    subject_code = fields.List(fields.String(), load_from='legSubject_code')
    territorial_subdivision = fields.String(
        load_from='legTerritorialSubdivision')
    type_code = fields.String(load_from='legTypeCode')
