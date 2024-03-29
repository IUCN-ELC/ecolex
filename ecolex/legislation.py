import json
import logging
import logging.config
import tempfile
import unicodedata
from datetime import datetime
from collections import OrderedDict

import requests
import lxml.etree as ET
from bs4 import BeautifulSoup
from pysolr import SolrError
from django.conf import settings
from django.template.defaultfilters import slugify

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import LEGISLATION
from ecolex.management.utils import EcolexSolr, clean_text_date
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger("legislation_import")

DOCUMENT = "document"
REPEALED = "repealed"
IN_FORCE = "in force"

FIELD_MAP = {
    "id": "legId",
    "FaolexId": "legId",
    "Title_of_Text": "legTitle",
    "Long_Title_of_text": "legLongTitle",
    "Serial_Imprint": "legSource",

    "Date_of_original_Text": "_legOriginalDate",
    "Date_of_Text": "legDate",
    "Date_of_Consolidation": "_legDateOfConsolidation", # not stored

    "Entry_into_Force": "legEntryIntoForce",

    "country_ISO": "legCountry_iso",
    "country": "_countryCodeAlt",
    "organization": "_organization_en",
    "organization_fr": "_organization_fr",
    "organization_es": "_organization_es",

    "Territorial_Subdivision": "legTerritorialSubdivision",
    "Sub_file_code": "legSubject_code",
    "basin_en": "legBasin_en",
    "basin_fr": "legBasin_fr",
    "basin_es": "legBasin_es",

    "Type_of_Text": "legTypeCode",

    "Related_Web_Site": "legRelatedWebSite",
    "link_to_full_text": "legLinkToFullText", # TODO: handle multiple files

    "Record_Language": "legLanguage_code",
    "Doc_Language": "legLanguage_en",

    "Abstract": "legAbstract",
    "keyword": "legKeyword_code",
    "mainClassifyingKeyword": "legMainKeyword_code",

    "implements": "legImplement",
    "amends": "legAmends",
    "repeals": "legRepeals",

    "implementsTre": "legImplementTreaty",
    "citesTre": "legCitesTreaty",
}

MULTIVALUED_FIELDS = [
    "legLanguage_en",
    "legSubject_code",
    "legKeyword_code",
    "legBasin_en", "legBasin_fr", "legBasin_es",
    "legImplement", "legAmends", "legRepeals",
    "legImplementTreaty", "legCitesTreaty",
]

LANGUAGE_FIELDS = ["legLanguage_en", "legLanguage_fr", "legLanguage_es"]


def strip_accents(s):
   return "".join(c for c in unicodedata.normalize("NFD", s)
                  if unicodedata.category(c) != "Mn")


def get_content(values):
    values = [v.text for v in values]
    return values


def harvest_file(upfile):
    logger.info(f"[Legislation] Harvest file started.")
    documents = ET.fromstring(upfile, parser=ET.XMLParser(recover=True))
    legislations = []
    count_ignored = 0

    with open(settings.SOLR_IMPORT["common"]["fao_subjects_xml"], encoding="utf-8") as f:
        bs = BeautifulSoup(f.read(), "xml")
        subjects = {subject.Classification_Sec_Area.string: subject
                    for subject in bs.findAll("dictionary_term")}

    with open(settings.SOLR_IMPORT["common"]["fao_keywords_xml"], encoding="utf-8") as f:
        bs = BeautifulSoup(f.read(), "xml")
        keywords = {keyword.Code.string: keyword for keyword in bs.findAll("dictionary_term")}

    with open(settings.SOLR_IMPORT["common"]["fao_regions_json"], encoding="utf-8") as f:
        json_regions = json.load(f)

    with open(settings.SOLR_IMPORT["common"]["fao_countries_json"], encoding="utf-8") as f:
        json_countries = json.load(f)

    with open(settings.SOLR_IMPORT["common"]["languages_json"], encoding="utf-8") as f:
        languages_codes = json.load(f)

    all_languages = {}
    for k, v in languages_codes.items():
        key = v["en"].lower()
        all_languages[key] = v
        if "en2" in v:
            key = v["en2"].lower()
            all_languages[key] = v

    for document in documents.iter("document"):
        legislation = {
            "type": LEGISLATION,
            "legLanguage_es": set(),
            "legLanguage_fr": set(),
            "legKeyword_code": [],
            "legKeyword_en": [],
            "legKeyword_fr": [],
            "legKeyword_es": [],
            "legSubject_en": [],
            "legSubject_fr": [],
            "legSubject_es": [],
        }

        for k, v in FIELD_MAP.items():
            field_values = get_content(document.findall(k))

            if field_values and v not in MULTIVALUED_FIELDS:
                field_values = field_values[0]

            if field_values:
                if v == "legMainKeyword_code":
                    if field_values in legislation["legKeyword_code"]:
                        legislation["legKeyword_code"].remove(field_values)
                    legislation["legKeyword_code"].insert(0, field_values)
                else:
                    legislation[v] = field_values

        #  remove duplicates
        for field_name in MULTIVALUED_FIELDS:
            field_values = legislation.get(field_name)
            if field_values:
                legislation[field_name] = list(
                    OrderedDict.fromkeys(field_values).keys())

        langs = legislation.get("legLanguage_en", [])
        legislation["legLanguage_en"] = set()
        for lang in langs:
            key = strip_accents(lang.lower().strip())
            if key in all_languages:
                for lang_field in LANGUAGE_FIELDS:
                    legislation[lang_field].add(all_languages[key][lang_field[-2:]])
            else:
                for lang_field in LANGUAGE_FIELDS:
                    legislation[lang_field].add(lang)
                logger.error(f"Language not found {lang} {legislation.get('legId')}")

        for lang_field in LANGUAGE_FIELDS:
            legislation[lang_field] = list(legislation[lang_field])

        legTypeCode = legislation.get("legTypeCode")
        if legTypeCode and legTypeCode == "A":
            # Ignore International agreements
            logger.debug(f"Ignoring international agreement {legislation.get('legId')}")
            count_ignored += 1
            continue
        elif legTypeCode in settings.DOC_TYPES:
            legislation["legType_en"] = settings.DOC_TYPES[legTypeCode].get("en")
            legislation["legType_fr"] = settings.DOC_TYPES[legTypeCode].get("fr")
            legislation["legType_es"] = settings.DOC_TYPES[legTypeCode].get("es")

        _set_language_fields(legislation, "legSubject_", subjects)
        _set_language_fields(legislation, "legKeyword_", keywords)

        # overwrite countries with names from the dictionary
        iso_country = (
            legislation.get("legCountry_iso") or
            legislation.get("_countryCodeAlt")
        )
        if iso_country:
            fao_country = json_countries.get(iso_country)
            if fao_country:
                legislation["legCountry_en"] = fao_country.get("en")
                legislation["legCountry_es"] = fao_country.get("es")
                legislation["legCountry_fr"] = fao_country.get("fr")

                region = json_regions.get(iso_country)
                if region:
                    legislation["legGeoArea_en"] = region.get("en", [])
                    legislation["legGeoArea_fr"] = region.get("fr", [])
                    legislation["legGeoArea_es"] = region.get("es", [])
                else:
                    logger.warning(f"No regions for country {iso_country}")
            else:
                logger.warning(f"Country not found: {iso_country}")
        else:
            # exception for the European Union
            if legislation.get("_organization_en") == "European Union":
                legislation["legCountry_en"] = "European Union"
                legislation["legCountry_fr"] = "Union européenne"
                legislation["legCountry_es"] = "Unión Europea"
                legislation["legGeoArea_en"] = "European Union Countries"
                legislation["legGeoArea_fr"] = "Países de la Unión Europea"
                legislation["legGeoArea_es"] = "Pays de l'Union Européenne"

        legDate = legislation.get("legDate") or legislation.get("_legDateOfConsolidation")

        if legDate:
            _, solr_format, dateValue = clean_text_date(legDate)
            if not dateValue or dateValue.year < 1700:
                if "legDate" in legislation:
                    del legislation["legDate"]
            else:
                legislation["legYear"] = dateValue.strftime("%Y")
                legislation["legDate"] = solr_format

        if "_legOriginalDate" in legislation:
            _, solr_format, dateValue = clean_text_date(legislation["_legOriginalDate"])
            if dateValue:
                legislation["legOriginalYear"] = dateValue.strftime("%Y")

        # XML may contain multiple files, but in ECOLEX it's single valued
        if "legLinkToFullText" in legislation:
            filename = legislation["legLinkToFullText"]
            extension = filename.rsplit(".")[-1].lower()
            url = settings.FULL_TEXT_URLS.get(extension)
            if url:
                legislation["legLinkToFullText"] = f"{url}{filename}"
            else:
                logger.error(f"URL not found for {filename} {legislation.get('legId')}")

        if (REPEALED.upper() in
                get_content(document.findall(REPEALED))):
            legislation["legStatus"] = REPEALED
            import ipdb; ipdb.set_trace()
        else:
            legislation["legStatus"] = IN_FORCE

        treaties = legislation.get("legImplementTreaty", [])
        cleaned_treaties = []
        for treaty in treaties:
            if treaty.endswith(".pdf"):
                treaty = treaty[:-4]
            cleaned_treaties.append(treaty)
        legislation["legImplementTreaty"] = cleaned_treaties

        title = legislation.get("legTitle") or legislation.get("legLongTitle")
        slug = title + " " + legislation.get("legId")
        legislation["slug"] = slugify(slug)

        # remove internal attributes
        legislations.append({
            key: value
            for key, value in legislation.items()
            if not key.startswith("_")
        })

    logger.info(f"[Legislation] Harvest file finished.")
    add_legislations(legislations, count_ignored)


def add_legislations(legislations, count_ignored):
    solr = EcolexSolr()
    count_updated = 0
    count_new = 0

    for legislation in legislations:
        leg_id = legislation.get("legId")
        logger.info(f"[Legislation] Adding {leg_id}")
        doc, _ = DocumentText.objects.get_or_create(
            doc_id=leg_id,
            url=legislation.get("legLinkToFullText")
        )
        doc.doc_type = LEGISLATION
        doc.status = DocumentText.INDEXED
        legislation["updatedDate"] = (datetime.now()
                                      .strftime("%Y-%m-%dT%H:%M:%SZ"))
        try:
            leg_existing = solr.search(LEGISLATION, leg_id)
            if leg_existing:
                legislation["id"] = leg_existing["id"]
            solr.add(legislation)
            # full-text extraction is done separately
            # see LegislationImporter.update_full_text
            doc.save()
            if leg_existing:
                count_updated += 1
            else:
                count_new += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error importing legislation {leg_id}")
            if settings.DEBUG:
                logger.exception(e)

    logger.info(f"Total {len(legislations) + count_ignored}. "
                f"Added {count_new}. Updated {count_updated}. "
                f"Failed {len(legislations) - count_new - count_updated}. "
                f"Ignored {count_ignored}")


def _set_language_fields(data, field, local_dict):
    """
    Set language fields (en, fr, es) for keywords and regions
    from dictionary, searching by codes found in new format XML
    """

    for field_value in data.get(f"{field}code", []):
        if field_value in local_dict:
            data[f"{field}en"].append(local_dict.get(field_value).Name_en_US.string)
            data[f"{field}fr"].append(local_dict.get(field_value).Name_fr_FR.string)
            data[f"{field}es"].append(local_dict.get(field_value).Name_es_ES.string)


# deprecated
def _set_values_from_dict(data, field, local_dict):
    """
    Switch language fields (en, fr, es) given in old format XML
    with updated values from internal dictionary
    """

    id_field = "legId"
    langs = ["en", "fr", "es"]
    fields = ["{}_{}".format(field, lang_code) for lang_code in langs]
    new_values = {x: [] for x in langs}
    if all(map((lambda x: x in data), fields)):
        values = zip(*[data[x] for x in fields])
        for val_en, val_fr, val_es in values:
            dict_values = local_dict.get(val_en.lower())
            if dict_values:
                new_values["en"].append(dict_values["en"])
                dict_value_fr = dict_values["fr"]
                dict_value_es = dict_values["es"]
                if val_fr != dict_value_fr:
                    logger.debug(f"{field}_fr name different: {data[id_field]} "
                                 f"{val_fr} {dict_value_fr}")
                new_values["fr"].append(dict_value_fr)
                if val_es != dict_value_es:
                    logger.debug(f"{field}_es name different: {data[id_field]} "
                                 f"{val_es} {dict_value_es}")
                new_values["es"].append(dict_value_es)
            else:
                logger.warning(f"New {field} name: {data[id_field]} {val_en} "
                               f"{val_fr} {val_es}")
                new_values["en"].append(val_en)
                new_values["fr"].append(val_fr)
                new_values["es"].append(val_es)
    elif fields[0] in data:
        values_en = data.get(fields[0], []) or []
        for val_en in values_en:
            dict_values = local_dict.get(val_en.lower())
            if dict_values:
                for lang in langs:
                    new_values[lang].append(dict_values[lang])
            else:
                logger.warning(f"New {field}_en name: {data[id_field]} {val_en}")
                new_values["en"].append(val_en)
    for field in fields:
        data[field] = new_values[field[-2:]]
