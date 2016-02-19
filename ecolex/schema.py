from marshmallow import Schema, fields, missing as missing_


# monkey patch default Field implementation to support mutilingual fields
# (it's simpler than extending every needed field type)
if not getattr(fields.Field, '_patched', False):
    def _patched_init(self, multilingual=False, fallback=True, **kwargs):
        self.multilingual = multilingual
        self.fallback = fallback

        self._orig_init(**kwargs)

    def _patched_get_value(self, attr, obj, accessor=None, default=missing_):
        # this logic is copy/paste from upstream
        attribute = getattr(self, 'attribute', None)
        accessor_func = accessor or fields.utils.get_value
        check_key = attr if attribute is None else attribute

        # TODO: raise error if multilingual and no language?
        lang = self.context.get('lang') if self.multilingual else None

        if not self.multilingual or not lang:
            ck = check_key
        elif not self.fallback:
            ck = "%s_%s" % (check_key, lang)

        if not self.multilingual or not lang or not self.fallback:
            return accessor_func(ck, obj, default)

        # if multilingual and fallback, try in order key_{lang}, key, key_en
        for ck in (
                "%s_%s" % (check_key, lang), check_key, "%s_en" % check_key):
            retval = accessor_func(ck, obj, default)
            if retval is not default:
                break
        return retval

    fields.Field._orig_init = fields.Field.__init__
    fields.Field.__init__ = _patched_init
    fields.Field.get_value = _patched_get_value
    fields.Field._patched = True


'''
###
# the fields below are obtained with:
###
$ ./manage.py shell --plain
>>> import urllib, json
>>> from django.conf import settings
>>> response = urllib.request.urlopen(settings.SOLR_URI + 'schema')
>>> data = json.loads(response.read().decode('utf-8'))
>>> for f in data['schema']['fields']:
...     print(f['name'], f['type'])
###
# fields that don't reflect in the schema have a ! prepended
# (except for the following, wich have yet to be put in their proper place)
###

docCountry string
docCountry_es string
docCountry_fr string
docDate tdate
docKeyword string
docLanguage string
docLanguage_es string
docLanguage_fr string
docRegion string
docRegion_es string
docRegion_fr string
docSubject string

evAbbreviation string
evAccess string
evCity text
evCountryId int
evDescription text
evEnd tdate
evEventUrl text
evId int
evIdEventPrevious int
evImage string
evImageCopyRight string
evIsIndexed boolean
evKind string
evLatitude double
evLocation string
evLongitude double
evOrganizationId int
evOriginalId string
evPersonId int
evRecAuthor text
evRecCreated tdate
evRecUpdated tdate
evRecUpdatedAuthor text
evRepetition text
evStart tdate
evStatus string
evTitle text
evTreatyId int
evType string
evUseInformea boolean

'''


# id string
# type string
# indexedDate tdate
# updatedDate tdate
#!globalText text_general
#!relatedwebsite string
#!source string
#!text text_general
#!doc_content text_general

class BaseSchema(Schema):
    """
    Inherited by all main object schemas.
    """
    id = fields.String()
    type = fields.String()
    indexed_at = fields.DateTime(load_from='indexedDate')
    updated_at = fields.DateTime(load_from='updatedDate')


    def load(self, *args, **kwargs):
        super().load(*args, **kwargs)

# partyCountry string
# partyDateOfAcceptanceApproval tdate
# partyDateOfAccessionApprobation tdate
# partyDateOfConsentToBeBound tdate
# partyDateOfDefiniteSignature tdate
# partyDateOfParticipation tdate
# partyDateOfProvisionalApplication tdate
# partyDateOfRatification tdate
# partyDateOfReservation tdate
# partyDateOfSimpleSignature tdate
# partyDateOfSuccession tdate
# partyDateOfWithdrawal tdate
# partyEntryIntoForce tdate

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


# trAbstract_en text
# trAbstract_es text
# trAbstract_fr text
# trAmendedBy string
# trAmendsTreaty string
# trAuthor text
# trAuthorA text
# trAuthorM text
# trAuthorWhole string
# trAvailableIn string
# trBasin_en text
# trBasin_es text
# trBasin_fr text
# trCitedBy string
# trCitesTreaty string
# trComment text
# trConfName text
# trConfPlace text
# trContributor text
# trCourtName text
# trDateOfConsolidation tdate
# trDateOfEntry tdate
# trDateOfLastLegalAction tdate
# trDateOfModification tdate
# trDateOfText tdate
# trDepository_en string
# trDepository_es string
# trDepository_fr string
# trDisplayDetails string
# trDisplayTitle string
# trDisplayTitle_En_US string
# trDisplayTitle_Fr_FR string
# trDisplayTitle_Sp_SP string
# trElisId string
# trEnabled string
# trEnabledByTreaty string
# trEnablesTreaty string
# trEntryIntoForceDate tdate
# trFieldOfApplication_en string
# trFieldOfApplication_es string
# trFieldOfApplication_fr string
# trInformeaId string
# trInternetReference_en string
# trInternetReference_es string
# trInternetReference_fr string
# trInternetReference_other string
# trIntoForceTreaty string
# trIntroText text
# trIsProtocol string
# trJurisdiction_en text
# trJurisdiction_es text
# trJurisdiction_fr text
# trKeyword_en text
# trKeyword_es text
# trKeyword_fr text
# trLanguageOfDocument_en text
# trLanguageOfDocument_es text
# trLanguageOfDocument_fr text
# trLanguageOfTranslation string
# trLinkToAbstract string
# trLinkToFullText_en string
# trLinkToFullText_es string
# trLinkToFullText_fr string
# trLinkToFullText_other string
# trLogoMedium text
# trNumberOfPages string
# trNumberOfParties text
# trObsolete string
# trOfficialPublication string
# trOrder string
# trPaperTitleOfText_en text
# trPaperTitleOfText_es text
# trPaperTitleOfText_fr text
# trPaperTitleOfText_other text
# trParentId int
# trPlaceOfAdoption string
# trPrimary text
# trPublisher text
# trReferenceToLiterature string
# trReferenceToTreaties string
# trRegion text
# trRelevantTextTreaty string
# trScope text
# trSearchDate tdate
# trSeatOfCourt text
# trStatus string
# trSubject_en text
# trSubject_es text
# trSubject_fr text
# trSupersededBy string
# trSupersedesTreaty string
# trThemeSecondary text
# trTitleAbbreviation text
# trTitleOfText text
# trTitleOfTextShort text
# trTypeOfText_en text
# trTypeOfText_es text
# trTypeOfText_fr text
# trUrl text
# trUrlElearning text
# trUrlParties text
# trUrlTreatyText text
# trUrlWikipedia text

class TreatySchema(BaseSchema):
    # setting these requires special handling, TODO
    parties = fields.Nested(TreatyPartySchema, many=True)
    abstract = fields.String(load_from='trAbstract', multilingual=True)
    '''
    # TO BE CONTINUED
    trAmendedBy string
    trAmendsTreaty string
    trAuthor text
    trAuthorA text
    trAuthorM text
    trAuthorWhole string
    trAvailableIn string
    trBasin_en text
    trBasin_es text
    trBasin_fr text
    trCitedBy string
    trCitesTreaty string
    trComment text
    trConfName text
    trConfPlace text
    trContributor text
    trCourtName text
    trDateOfConsolidation tdate
    trDateOfEntry tdate
    trDateOfLastLegalAction tdate
    trDateOfModification tdate
    trDateOfText tdate
    trDepository_en string
    trDepository_es string
    trDepository_fr string
    trDisplayDetails string
    trDisplayTitle string
    trDisplayTitle_En_US string
    trDisplayTitle_Fr_FR string
    trDisplayTitle_Sp_SP string
    trElisId string
    trEnabled string
    trEnabledByTreaty string
    trEnablesTreaty string
    trEntryIntoForceDate tdate
    trFieldOfApplication_en string
    trFieldOfApplication_es string
    trFieldOfApplication_fr string
    trInformeaId string
    trInternetReference_en string
    trInternetReference_es string
    trInternetReference_fr string
    trInternetReference_other string
    trIntoForceTreaty string
    trIntroText text
    trIsProtocol string
    trJurisdiction_en text
    trJurisdiction_es text
    trJurisdiction_fr text
    trKeyword_en text
    trKeyword_es text
    trKeyword_fr text
    trLanguageOfDocument_en text
    trLanguageOfDocument_es text
    trLanguageOfDocument_fr text
    trLanguageOfTranslation string
    trLinkToAbstract string
    trLinkToFullText_en string
    trLinkToFullText_es string
    trLinkToFullText_fr string
    trLinkToFullText_other string
    trLogoMedium text
    trNumberOfPages string
    trNumberOfParties text
    trObsolete string
    trOfficialPublication string
    trOrder string
    trPaperTitleOfText_en text
    trPaperTitleOfText_es text
    trPaperTitleOfText_fr text
    trPaperTitleOfText_other text
    trParentId int
    trPlaceOfAdoption string
    trPrimary text
    trPublisher text
    trReferenceToLiterature string
    trReferenceToTreaties string
    trRegion text
    trRelevantTextTreaty string
    trScope text
    trSearchDate tdate
    trSeatOfCourt text
    trStatus string
    trSubject_en text
    trSubject_es text
    trSubject_fr text
    trSupersededBy string
    trSupersedesTreaty string
    trThemeSecondary text
    trTitleAbbreviation text
    trTitleOfText text
    trTitleOfTextShort text
    trTypeOfText_en text
    trTypeOfText_es text
    trTypeOfText_fr text
    trUrl text
    trUrlElearning text
    trUrlParties text
    trUrlTreatyText text
    trUrlWikipedia text
    '''


# decBody text
# decId string
# decKeyword text
# decLanguage string
# decLink string
# decLongTitle_ar string
# decLongTitle_en string
# decLongTitle_es string
# decLongTitle_fr string
# decLongTitle_ru string
# decLongTitle_zh string
# decMeetingId string
# decMeetingTitle string
# decMeetingUrl string
# decNumber string
# decPublishDate tdate
# decShortTitle_ar string
# decShortTitle_en string
# decShortTitle_es string
# decShortTitle_fr string
# decShortTitle_ru string
# decShortTitle_zh string
# decStatus string
# decSummary string
# decText text
# decTitleOfText text
# decTreaty string
# decTreatyId string
# decTreatyName_en string
# decTreatyName_es string
# decTreatyName_fr string
# decType string
# decUpdateDate tdate

class DecisionSchema(BaseSchema):
    body = fields.String(load_from='decBody')
    # TODO: move this to base
    keywords = fields.List(fields.String(), load_from='decKeyword')
    '''
    # TO BE CONTINUED
    decId string
    decLanguage string
    decLink string
    decLongTitle_ar string
    decLongTitle_en string
    decLongTitle_es string
    decLongTitle_fr string
    decLongTitle_ru string
    decLongTitle_zh string
    decMeetingId string
    decMeetingTitle string
    decMeetingUrl string
    decNumber string
    decPublishDate tdate
    decShortTitle_ar string
    decShortTitle_en string
    decShortTitle_es string
    decShortTitle_fr string
    decShortTitle_ru string
    decShortTitle_zh string
    decStatus string
    decSummary string
    decText text
    decTitleOfText text
    decTreaty string
    decTreatyId string
    decTreatyName_en string
    decTreatyName_es string
    decTreatyName_fr string
    decType string
    decUpdateDate tdate
    '''


# litAbstract text
# litAbstract_fr text
# litAbstract_other text
# litAbstract_sp text
# litAuthor string
# litAuthorArticle string
# litAvailableIn string
# litBasin string
# litBasin_fr string
# litBasin_sp string
# litCallNo string
# litCollation string
# litConfDate string
# litConfName text
# litConfName_fr text
# litConfName_other text
# litConfName_sp text
# litConfNo string
# litConfPlace string
# litContributor text
# litCorpAuthor string
# litCorpAuthorArticle string
# litCountry string
# litCountry_fr string
# litCountry_sp string
# litCourtDecisionReference string
# litDateOfEntry tdate
# litDateOfModification tdate
# litDateOfText string
# litDateOfTextSer string
# litDisplayDetails text
# litDisplayRegion text
# litDisplayRegion_fr text
# litDisplayRegion_sp text
# litDisplayTitle text
# litEULegislationReference string
# litEdition string
# litFaolexReference string
# litFormerTitle string
# litFrequency string
# litHoldings string
# litISBN string
# litISSN string
# litId string
# litId2 string
# litIntOrg string
# litIntOrg_fr string
# litIntOrg_sp string
# litInternetReference string
# litKeyword text
# litKeyword_fr text
# litKeyword_sp text
# litLanguageOfDocument string
# litLanguageOfDocument_fr string
# litLanguageOfDocument_sp string
# litLanguageOfTranslation string
# litLanguageOfTranslation_fr string
# litLanguageOfTranslation_sp string
# litLinkDOI string
# litLinkToAbstract string
# litLinkToFullText string
# litLiteratureReference string
# litLocation string
# litLongTitle text
# litLongTitle_fr text
# litLongTitle_other text
# litLongTitle_sp text
# litModeOfAcquisition string
# litNationalLegislationReference string
# litPaperTitleOfText text
# litPaperTitleOfText_fr text
# litPaperTitleOfText_other text
# litPaperTitleOfText_sp text
# litPublPlace string
# litPublisher string
# litRegion string
# litRegion_fr string
# litRegion_sp string
# litRelatedMonograph string
# litRelatedWebSite string
# litScope text
# litScope_fr text
# litScope_sp text
# litSearchDate string
# litSerialStatus string
# litSerialTitle string
# litSeriesFlag string
# litSubject text
# litSubject_fr text
# litSubject_sp text
# litTerritorialSubdivision string
# litTerritorialSubdivision_fr string
# litTerritorialSubdivision_sp string
# litTitleAbbreviation string
# litTitleOfTextShort text
# litTitleOfTextShort_fr text
# litTitleOfTextShort_other text
# litTitleOfTextShort_sp text
# litTitleOfTextTransl text
# litTitleOfTextTransl_fr text
# litTitleOfTextTransl_sp text
# litTreatyReference string
# litTypeOfText string
# litTypeOfText_fr string
# litTypeOfText_sp string
# litVolumeNo string

class LiteratureSchema(BaseSchema):
    # TODO: what kind of multilingual is this?
    abstract = fields.String(load_from='litAbstract', multilingual=True)
    '''
    # TO BE CONTINUED
    litAbstract text
    litAbstract_fr text
    litAbstract_other text
    litAbstract_sp text
    litAuthor string
    litAuthorArticle string
    litAvailableIn string
    litBasin string
    litBasin_fr string
    litBasin_sp string
    litCallNo string
    litCollation string
    litConfDate string
    litConfName text
    litConfName_fr text
    litConfName_other text
    litConfName_sp text
    litConfNo string
    litConfPlace string
    litContributor text
    litCorpAuthor string
    litCorpAuthorArticle string
    litCountry string
    litCountry_fr string
    litCountry_sp string
    litCourtDecisionReference string
    litDateOfEntry tdate
    litDateOfModification tdate
    litDateOfText string
    litDateOfTextSer string
    litDisplayDetails text
    litDisplayRegion text
    litDisplayRegion_fr text
    litDisplayRegion_sp text
    litDisplayTitle text
    litEULegislationReference string
    litEdition string
    litFaolexReference string
    litFormerTitle string
    litFrequency string
    litHoldings string
    litISBN string
    litISSN string
    litId string
    litId2 string
    litIntOrg string
    litIntOrg_fr string
    litIntOrg_sp string
    litInternetReference string
    litKeyword text
    litKeyword_fr text
    litKeyword_sp text
    litLanguageOfDocument string
    litLanguageOfDocument_fr string
    litLanguageOfDocument_sp string
    litLanguageOfTranslation string
    litLanguageOfTranslation_fr string
    litLanguageOfTranslation_sp string
    litLinkDOI string
    litLinkToAbstract string
    litLinkToFullText string
    litLiteratureReference string
    litLocation string
    litLongTitle text
    litLongTitle_fr text
    litLongTitle_other text
    litLongTitle_sp text
    litModeOfAcquisition string
    litNationalLegislationReference string
    litPaperTitleOfText text
    litPaperTitleOfText_fr text
    litPaperTitleOfText_other text
    litPaperTitleOfText_sp text
    litPublPlace string
    litPublisher string
    litRegion string
    litRegion_fr string
    litRegion_sp string
    litRelatedMonograph string
    litRelatedWebSite string
    litScope text
    litScope_fr text
    litScope_sp text
    litSearchDate string
    litSerialStatus string
    litSerialTitle string
    litSeriesFlag string
    litSubject text
    litSubject_fr text
    litSubject_sp text
    litTerritorialSubdivision string
    litTerritorialSubdivision_fr string
    litTerritorialSubdivision_sp string
    litTitleAbbreviation string
    litTitleOfTextShort text
    litTitleOfTextShort_fr text
    litTitleOfTextShort_other text
    litTitleOfTextShort_sp text
    litTitleOfTextTransl text
    litTitleOfTextTransl_fr text
    litTitleOfTextTransl_sp text
    litTreatyReference string
    litTypeOfText string
    litTypeOfText_fr string
    litTypeOfText_sp string
    litVolumeNo string


# cdAbstract text
# cdAbstractOther string
# cdAbstract_en text
# cdAbstract_es text
# cdAbstract_fr text
# cdAbstract_ru text
# cdAlternativeRecordId string
# cdAvailableIn string
# cdCountry_en string
# cdCountry_es string
# cdCountry_fr string
# cdCourtDecisionIdNumber string
# cdCourtDecisionReference string
# cdCourtDecisionSubdivision string
# cdCourtName string
# cdDateOfEntry tdate
# cdDateOfModification tdate
# cdDateOfText tdate
# cdEcolexUrl string
# cdEcolexUrl_en string
# cdEcolexUrl_es string
# cdEcolexUrl_fr string
# cdEcolexUrl_ru string
# cdFaolexReference string
# cdFaolexUrl string
# cdFaolexUrl_en string
# cdFaolexUrl_es string
# cdFaolexUrl_fr string
# cdFaolexUrl_ru string
# cdFiles string
# cdInformeaTags string
# cdInstance string
# cdInternetReference string
# cdInternetReference_en string
# cdInternetReference_es string
# cdInternetReference_fr string
# cdInternetReference_ru string
# cdIsisNumber string
# cdJurisdiction string
# cdJustices string
# cdKeywords text
# cdLanguageOfDocument string
# cdLeoId string
# cdLinkToFullText string
# cdLinkToFullText_en string
# cdLinkToFullText_es string
# cdLinkToFullText_fr string
# cdLinkToFullText_ru string
# cdNotes string
# cdNumberOfPages int
# cdOfficialPublication string
# cdOriginalId string
# cdReferenceNumber string
# cdReferenceToLegislation string
# cdRegion string
# cdRelatedUrl string
# cdRelatedUrl_en string
# cdRelatedUrl_es string
# cdRelatedUrl_fr string
# cdRelatedUrl_ru string
# cdSeatOfCourt string
# cdSeatOfCourt_en string
# cdSeatOfCourt_es string
# cdSeatOfCourt_fr string
# cdSeatOfCourt_ru string
# cdStatusOfDecision string
# cdSubject text
# cdTerritorialSubdivision_en string
# cdTerritorialSubdivision_es string
# cdTerritorialSubdivision_fr string
# cdTitleOfText text
# cdTitleOfTextOther string
# cdTitleOfTextShort string
# cdTitleOfText_en text
# cdTitleOfText_es text
# cdTitleOfText_fr text
# cdTitleOfText_ru text
# cdTreatyReference string
# cdTypeOfText string
# cdUrlOther string
    '''

class CourtDecisionSchema(BaseSchema):
    # TODO: what kind of multilingual is this?
    # TODO: this is common to more. group together?
    abstract = fields.String(load_from='cdAbstract', multilingual=True)
    '''
    # TO BE CONTINUED
    cdAbstract text
    cdAbstractOther string
    cdAbstract_en text
    cdAbstract_es text
    cdAbstract_fr text
    cdAbstract_ru text
    cdAlternativeRecordId string
    cdAvailableIn string
    cdCountry_en string
    cdCountry_es string
    cdCountry_fr string
    cdCourtDecisionIdNumber string
    cdCourtDecisionReference string
    cdCourtDecisionSubdivision string
    cdCourtName string
    cdDateOfEntry tdate
    cdDateOfModification tdate
    cdDateOfText tdate
    cdEcolexUrl string
    cdEcolexUrl_en string
    cdEcolexUrl_es string
    cdEcolexUrl_fr string
    cdEcolexUrl_ru string
    cdFaolexReference string
    cdFaolexUrl string
    cdFaolexUrl_en string
    cdFaolexUrl_es string
    cdFaolexUrl_fr string
    cdFaolexUrl_ru string
    cdFiles string
    cdInformeaTags string
    cdInstance string
    cdInternetReference string
    cdInternetReference_en string
    cdInternetReference_es string
    cdInternetReference_fr string
    cdInternetReference_ru string
    cdIsisNumber string
    cdJurisdiction string
    cdJustices string
    cdKeywords text
    cdLanguageOfDocument string
    cdLeoId string
    cdLinkToFullText string
    cdLinkToFullText_en string
    cdLinkToFullText_es string
    cdLinkToFullText_fr string
    cdLinkToFullText_ru string
    cdNotes string
    cdNumberOfPages int
    cdOfficialPublication string
    cdOriginalId string
    cdReferenceNumber string
    cdReferenceToLegislation string
    cdRegion string
    cdRelatedUrl string
    cdRelatedUrl_en string
    cdRelatedUrl_es string
    cdRelatedUrl_fr string
    cdRelatedUrl_ru string
    cdSeatOfCourt string
    cdSeatOfCourt_en string
    cdSeatOfCourt_es string
    cdSeatOfCourt_fr string
    cdSeatOfCourt_ru string
    cdStatusOfDecision string
    cdSubject text
    cdTerritorialSubdivision_en string
    cdTerritorialSubdivision_es string
    cdTerritorialSubdivision_fr string
    cdTitleOfText text
    cdTitleOfTextOther string
    cdTitleOfTextShort string
    cdTitleOfText_en text
    cdTitleOfText_es text
    cdTitleOfText_fr text
    cdTitleOfText_ru text
    cdTreatyReference string
    cdTypeOfText string
    cdUrlOther string
    '''


# legAbstract text
# legAmends string
# legConsolidationDate tdate
# legCountry_en string
# legCountry_es string
# legCountry_fr string
# legCountry_iso string
# legDate tdate
# legEntryDate tdate
# legEntryIntoForce string
# legGeoArea_en string
# legGeoArea_es string
# legGeoArea_fr string
# legId string
# legImplement string
# legKeyword_code string
# legKeyword_en text
# legKeyword_es text
# legKeyword_fr text
# legLanguage_code string
# legLanguage_en string
# legLanguage_es string
# legLanguage_fr string
# legLinkToFullText string
# legLongTitle text
# legModificationDate tdate
# legOriginalDate tdate
# legRelatedWebSite string
# legRepeals string
# legSearchDate tdate
# legSource string
# legStatus string
# legSubject_code string
# legSubject_en text
# legSubject_es text
# legSubject_fr text
# legTerritorialSubdivision string
# legTitle text
# legTypeCode string
# legType_en string
# legType_es string
# legType_fr string

class LegislationSchema(BaseSchema):
    abstract = fields.String(load_from='legAbstract')
    consolidation_date = fields.Date(load_from='legConsolidationDate')
    date = fields.Date(load_from='legDate')
    entry_date = fields.Date(load_from='legEntryDate')
    country = fields.String(load_from='legCountry', multilingual=True)
    country_iso = fields.String(load_from='legCountry_iso')
    '''
    # TO BE CONTINUED

    legAmends string
    legEntryIntoForce string
    legGeoArea_en string
    legGeoArea_es string
    legGeoArea_fr string
    legId string
    legImplement string
    legKeyword_code string
    legKeyword_en text
    legKeyword_es text
    legKeyword_fr text
    legLanguage_code string
    legLanguage_en string
    legLanguage_es string
    legLanguage_fr string
    legLinkToFullText string
    legLongTitle text
    legModificationDate tdate
    legOriginalDate tdate
    legRelatedWebSite string
    legRepeals string
    legSearchDate tdate
    legSource string
    legStatus string
    legSubject_code string
    legSubject_en text
    legSubject_es text
    legSubject_fr text
    legTerritorialSubdivision string
    legTitle text
    legTypeCode string
    legType_en string
    legType_es string
    legType_fr string
    '''
