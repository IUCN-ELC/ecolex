"""
These models define the documents' behaviour that could not be included in the
schema. They will eventually replace actual solr_models.
"""
from collections import defaultdict
from datetime import date
from functools import partialmethod
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from django.utils.translation import get_language
from ecolex.lib.utils import is_iterable, camel_case_to__


DEFAULT_TITLE = 'Unknown Document'
INVALID_DATE = date(2, 11, 30)

# This limit does not allow all documents to be showed on the details_decisions,
# details_court_decisions and details_literatures pages (Treaty -> Other
# references). However, increasing this limit also increases the page's
# load time. TODO Pagination on the details pages
MAX_ROWS = 100


def join_available_values(separator, *values):
    return separator.join([v for v in values if v])


class BaseModel(object):
    @property
    def type(self):
        return camel_case_to__(self.__class__.__name__)

    def __init__(self, **kwargs):
        # set everything as attrs
        for k, v in kwargs.items():
            # (except for type)
            if k == 'type':
                if v != self.type:
                    raise ValueError("Object is of type '%s' but received "
                                     "type '%s'." % (self.type, v))
                continue

            setattr(self, k, v)


class DocumentModel(BaseModel):
    REFERENCES = []
    BACKREFERENCES = {}
    OTHER_REFERENCES = {}

    @property
    def details_url(self):
        return reverse(self.URL_NAME, kwargs={'slug': self.slug})

    def _resolve_field(self, field, type=None):
        if type is None:
            type = self.type
        # TODO: this is ugly. schema map should be.. better...
        from . import schema
        sch = schema.SCHEMA_MAP[type]
        field = "%s_%s" % (sch.opts.abbr, field)
        return schema.FIELD_PROPERTIES[type][field].get_source_field()

    @cached_property
    def references(self):
        """
        Relationships with documents of the same type.
        """
        lookups = {}
        groupers = {}
        fields = set()

        from .xsearch import Queryer
        queryer = Queryer({}, language=get_language())

        for ref in self.REFERENCES:
            try:
                backref = self.BACKREFERENCES[ref]
            except KeyError:
                # if it's a forward reference, we search for documents with
                # document_id matching the current value
                field = 'document_id'
                try:
                    lookup = getattr(self, ref)
                except AttributeError:
                    continue
            else:
                # if it's a backwards reference, we search for documents
                # whose reverse attribute contains our document_id
                field = backref
                lookup = self.document_id

            fields.add(field)
            groupers[ref] = (field, lookup)
            # TODO: field resolving logic should live in search,
            # the models shouldn't be aware of the underlying data structure.
            lookup_field = self._resolve_field(field)
            if lookup_field in lookups:
                # these better be both lists
                lookups[lookup_field].extend(lookup)
            else:
                lookups[lookup_field] = lookup

        if not lookups:
            return {}

        # (this is getting really, really silly)
        from .schema import FIELD_PROPERTIES
        fields = [f for f in FIELD_PROPERTIES[self.type].values()
                  if f.name in fields]

        # set a ridiculously high page size to be certain we fetch all results
        # TODO: may be a bad™ idea
        response = queryer.findany(page_size=1000, fetch_fields=fields,
                                   date_sort=False, **lookups)

        # we need to re-group according to the lookups
        out = defaultdict(list)
        for item in response.results:
            for k, v in groupers.items():
                field, lookup = v
                try:
                    val = getattr(item, field)
                except AttributeError:
                    continue

                if ((is_iterable(val)
                     and (is_iterable(lookup) and set(lookup).intersection(val)
                          or lookup in val)
                     ) or
                    (is_iterable(lookup) and val in lookup
                     or lookup == val)
                ):
                    out[k].append(item)
                    # don't break on a positive match, because a document
                    # might belong in multiple categories

        # and re-order
        return {
            k: out[k]
            for k in self.REFERENCES
            if k in out
        }

    @cached_property
    def other_references(self):
        """
        Returns counts of relationships with objects of different types.
        """
        from .xsearch import DEFAULT_INTERFACE as interface
        Q = interface.Q

        q = Q()

        for typ, v in self.OTHER_REFERENCES.items():
            remote_field, local_field = v
            try:
                value = getattr(self, local_field)
            except AttributeError:
                continue

            q |= Q(**{self._resolve_field(remote_field, typ): value})

        if not q:
            return {}

        response = (
            interface.query()
            .filter(q)
            .facet_by('type', mincount=1)
            .paginate(rows=0)
            .execute()
        )

        return dict(response.facet_counts.facet_fields['type'])

    def _get_reference_count(self, typ):
        try:
            return self.other_references[typ]
        except KeyError:
            return 0


class Treaty(DocumentModel):
    URL_NAME = 'treaty_details'
    ID_FIELD = 'trElisId'
    EVENTS_NAMES = {
        'acceptance_approval': 'Acceptance/approval',
        'accession_approbation': 'Accession/approbation',
        'consent_to_be_bound': 'Consent to be bound',
        'definite_signature': 'Definite signature',
        'entry_into_force': 'Entry into force',
        'participation': 'Participation',
        'provisional_application': 'Provisional application',
        'ratification': 'Ratification',
        'ratification_group': 'Ratification *',
        'reservation': 'Reservation',
        'simple_signature': 'Simple signature',
        'succession': 'Succession',
        'withdrawal': 'Withdrawal',
    }
    EVENTS_ORDER = [
        'entry_into_force',
        'ratification_group',
        'simple_signature',
        'provisional_application',
        'participation',
        'reservation',
        'withdrawal',
    ]
    REFERENCES = [
        'enables', 'supersedes', 'cites', 'amends',
        'enabled_by', 'superseded_by', 'cited_by', 'amended_by',
    ]
    BACKREFERENCES = {
        'amended_by': 'amends',
        'cited_by': 'cites',
        'enables': 'enabled_by',
        'superseded_by': 'supersedes',
    }
    OTHER_REFERENCES = {
        'decision': ('treaty_id', 'informea_id'),
        'literature': ('treaty_reference', 'document_id'),
        'court_decision': ('treaty_reference', 'document_id'),
    }


    @property
    def title(self):
        return (self.title_of_text or
                self.title_of_text_short or
                self.title_abbreviation or
                DEFAULT_TITLE)

    @property
    def date(self):
        return (self.date_of_text or
                self.date_of_entry or
                self.date_of_modification)

    @cached_property
    def parties_events(self):
        events = set().union(*[party.events for party in self.parties])
        return sorted(events, key=lambda x: self.EVENTS_ORDER.index(x))

    @property
    def decision_count(self):
        return self._get_reference_count('decision')

    @property
    def literature_count(self):
        return self._get_reference_count('literature')

    @property
    def court_decision_count(self):
        return self._get_reference_count('court_decision')

    @cached_property
    def decisions(self):
        # TODO: refactor here
        if hasattr(self, 'informea_id'):
            from ecolex.search import get_documents_by_field
            return get_documents_by_field('decTreatyId', [self.informea_id], rows=MAX_ROWS)

    @cached_property
    def literatures(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('litTreatyReference',
                                      [self.document_id], rows=MAX_ROWS)

    @cached_property
    def court_decisions(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('cdTreatyReference',
                                      [self.document_id], rows=MAX_ROWS)


class TreatyParty(BaseModel):
    FIELD_GROUPS = {
        'ratification_group': [
            'ratification',
            'accession_approbation',
            'acceptance_approval',
            'succession',
            'consent_to_be_bound',
            'definite_signature',
        ]
    }
    GROUPED_FIELDS = {field: group
                      for group, fields in FIELD_GROUPS.items()
                      for field in fields}

    def __init__(self, **kwargs):
        self.country = kwargs.pop('country')
        self.events = []

        # This could be prettier
        for k, v in kwargs.items():
            key = k
            v = v if v != INVALID_DATE else None
            value = {'date': v, 'details': k}
            if k in self.GROUPED_FIELDS:
                key = self.GROUPED_FIELDS[k]
                value['details'] = k
                value['index'] = self.FIELD_GROUPS[key].index(k) + 1
            setattr(self, key, value)
            self.events.append(key)


class Decision(DocumentModel):
    URL_NAME = 'decision_details'

    @property
    def title(self):
        return self.short_title

    @property
    def date(self):
        return self.publish_date or self.update_date

    @cached_property
    def treaty(self):
        from ecolex.search import get_treaty_by_informea_id
        return get_treaty_by_informea_id(self.treaty_id)

    @cached_property
    def files(self):
        return list(zip(self.file_urls, self.file_names))

    @cached_property
    def language_names(self):
        return [settings.LANGUAGE_MAP.get(code, 'Undefined') for code in self.language]


class Legislation(DocumentModel):
    URL_NAME = 'legislation_details'
    ID_FIELD = 'legId'
    REFERENCES = [
        'implements', 'amends', 'repeals',
        'implemented_by', 'amended_by', 'repealed_by',
    ]
    BACKREFERENCES = {
        'amended_by': 'amends',
        'implemented_by': 'implements',
        'repealed_by': 'repeals',
    }

    @property
    def title(self):
        return self.short_title or self.long_title


class CourtDecision(DocumentModel):
    URL_NAME = 'court_decision_details'

    @property
    def title(self):
        return self.title_of_text

    @property
    def date(self):
        return self.date_of_text


class Literature(DocumentModel):
    URL_NAME = 'literature_details'

    @property
    def title(self):
        if self.document_id.startswith('ANA'):
            return self.paper_title_of_text
        elif self.document_id.startswith('MON'):
            return self.long_title
        return DEFAULT_TITLE

    @cached_property
    def people_authors(self):
        return self.author_a or self.author_m

    @cached_property
    def corp_authors(self):
        return self.corp_author_a or self.corp_author_m

    @property
    def authors(self):
        return self.people_authors or self.corp_authors

    @property
    def parent_url(self):
        # only for chapters
        from ecolex.search import get_documents_by_field
        if self.is_chapter and self.related_monograph:
            docs = get_documents_by_field('litId', [self.related_monograph], rows=1)
            if len(docs) > 0:
                doc = [x for x in docs][0]
                return doc.details_url
        return None

    @property
    def parent_title(self):
        if self.is_chapter:
            return self.long_title
        return None

    def date(self):
        return self.date_of_text_ser or self.year_of_text or self.date_of_text

    @cached_property
    def is_article(self):
        # TODO: also check document_id ?
        return bool(self.date_of_text_ser)

    @cached_property
    def is_chapter(self):
        return self.document_id.startswith('ANA') and not self.is_article

    @cached_property
    def serial_title(self):
        if self.is_article:
            # TODO: why don't we include always volume and collation
            # since they are always displayed together?
            return self.orig_serial_title
        else:
            # TODO: when is this shown???
            return join_available_values(' | ',
                                         self.orig_serial_title, self.volume_no)

    @cached_property
    def conference(self):
        return join_available_values(' | ',
                                     self.conf_name, self.conf_no,
                                     self.conf_date, self.conf_place)

    @cached_property
    def treaties(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('trElisId', self.treaty_reference,
                                      rows=MAX_ROWS)

    @cached_property
    def legislations(self):
        from ecolex.search import get_documents_by_field
        refs = (self.faolex_reference +
                self.eu_legislation_reference +
                self.national_legislation_reference)
        return get_documents_by_field('legId', refs, rows=MAX_ROWS)

    @cached_property
    def court_decisions(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('cdOriginalId',
                                      self.court_decision_reference,
                                      rows=MAX_ROWS)

    @cached_property
    def literatures(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('litId', self.literature_reference,
                                      rows=MAX_ROWS)

    @cached_property
    def references(self):
        # TODO. why the special case?
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('litLiteratureReference',
                                      [self.document_id], rows=MAX_ROWS)
