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

from ecolex.lib.utils import (
    OrderedDefaultDict, any_match, camel_case_to__, is_iterable
)


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
            return defaultdict(list)

        # (this is getting really, really silly)
        from .schema import FIELD_PROPERTIES
        extra_fields = [f for f in FIELD_PROPERTIES[self.type].values()
                        if f.name in fields]

        # set a ridiculously high page size to be certain we fetch all results
        # TODO: may be a bad™ idea
        response = queryer.findany(page_size=1000, fetch_fields=extra_fields,
                                   date_sort=False, **lookups)

        # we need to re-group according to the lookups
        out = OrderedDefaultDict(list)
        for item in response.results:
            for k, v in groupers.items():
                field, lookup = v
                try:
                    val = getattr(item, field)
                except AttributeError:
                    continue

                if any_match(val, lookup):
                    out[k].append(item)
                    # don't break on a positive match, because a document
                    # might belong in multiple categories

        # and re-order
        for k in self.REFERENCES:
            try:
                out.move_to_end(k)
            except KeyError:
                pass

        # this is needed because django's template goes funny with defaultdicts
        out.default_factory = None

        return out

    # TODO: this could easily be merged with `references` above
    @cached_property
    def _all_references(self):
        """
        Fetches all existing relationships in one go.
        """

        _BY_TYPE = defaultdict(list)
        fields = set()
        lookups = {}

        for name, v in self.CROSSREFERENCES.items():
            remote, lookup_field = v
            typ, field = remote.split(".")

            if not is_iterable(lookup_field):
                try:
                    lookup = getattr(self, lookup_field)
                except AttributeError:
                    continue
            else:
                lookup = []
                for lf in lookup_field:
                    try:
                        _look += getattr(self, lf)
                    except AttributeError:
                        continue
                    else:
                        if not is_iterable(_look):
                            _look = [_look]
                        lookup += _look

            if not lookup:
                continue

            _BY_TYPE[typ].append(name)
            fields.add((typ, field))

            lookup_field = self._resolve_field(field, typ)
            lookups[lookup_field] = lookup

        if not lookups:
            return defaultdict(list)

        # (yup, silly)
        from .schema import FIELD_PROPERTIES
        extra_fields = [f
                        for t, name in fields
                        for f in FIELD_PROPERTIES[t].values()
                        if f.name in fields]

        from .xsearch import Queryer
        queryer = Queryer({}, language=get_language())

        response = queryer.findany(page_size=1000, fetch_fields=extra_fields,
                                   date_sort=False, **lookups)

        out = defaultdict(list)
        for item in response.results:
            names = _BY_TYPE[item.type]
            # if there's only one lookup by that type,
            # this item is guaranteed to match
            if len(names) == 1:
                out[names[0]].append(item)
                continue

            for name in names:
                _t, field, lookup = self.CROSSREFERENCES[name]

                try:
                    val = getattr(item, field)
                except AttributeError:
                    continue

                if any_match(val, lookup):
                    out[name].append(item)
                    break

        return out

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
    CROSSREFERENCES = {
        'legislations_implemented_by': (
            'legislation.treaty_implements', 'document_id'),
        'legislations_cited_by': (
            'legislation.treaty_cites', 'document_id'),
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

    @property
    def legislations_implemented_by(self):
        return self._all_references['legislations_implemented_by']

    @property
    def legislations_cited_by(self):
        return self._all_references['legislations_cited_by']


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
        self.country_en = kwargs.pop('country_en')
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

    @property
    def files(self):
        return list(zip(self.file_urls, self.file_names))

    @property
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
    CROSSREFERENCES = {
        'treaties_implements': (
            'treaty.document_id', 'treaty_implements'),
        'treaties_cites': (
            'treaty.document_id', 'treaty_cites'),
        'court_decisions': (
            'court_decision.legislation_reference', 'document_id'),
    }

    @property
    def title(self):
        return self.short_title or self.long_title

    @property
    def court_decisions(self):
        return self._all_references['court_decisions']

    @property
    def treaties_implemented(self):
        return self._all_references['treaties_implements']

    @property
    def treaties_cited(self):
        return self._all_references['treaties_cites']


class CourtDecision(DocumentModel):
    URL_NAME = 'court_decision_details'
    REFERENCES = [
        'cites', 'cited_by',
    ]
    BACKREFERENCES = {
        'cited_by': 'cites'
    }
    CROSSREFERENCES = {
        'treaties': (
            'treaty.document_id', 'treaty_reference'),
        'legislation': (
            'legislation.document_id', 'legislation_reference'),
        #'cited_court_decisions': (
        #    'court_decision.document_id', 'cites'),
        #'cited_by_court_decisions': (
        #    'court_decision.cites', 'document_id'),
    }

    @property
    def title(self):
        return self.title_of_text

    @property
    def date(self):
        return self.date_of_text

    @property
    def treaties(self):
        return self._all_references['treaties']

    @property
    def legislation(self):
        return self._all_references['legislation']


class Literature(DocumentModel):
    URL_NAME = 'literature_details'

    REFERENCES = [
        'literature_reference',
        'referenced_by',
    ]
    BACKREFERENCES = {
        'referenced_by': 'literature_reference',
    }
    CROSSREFERENCES = {
        'treaties': (
            'treaty.document_id', 'treaty_reference'),
        'legislations': (
            'legislation.document_id', (
                'faolex_reference', 'eu_legislation_reference',
                'national_legislation_reference')),
        'court_decisions': (
            'court_decision.original_id', 'court_decision_reference'),
        'literatures': (
            'literature.document_id', 'literature_reference'),
        'references': (
            'literature.literature_reference', 'document_id')
    }

    @property
    def title(self):
        if self.document_id.startswith('ANA'):
            return self.paper_title_of_text
        elif self.document_id.startswith('MON'):
            return self.long_title
        return DEFAULT_TITLE

    @property
    def people_authors(self):
        return self.author_a or self.author_m

    @property
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

    @property
    def is_article(self):
        # TODO: also check document_id ?
        return bool(self.date_of_text_ser)

    @property
    def is_chapter(self):
        return self.document_id.startswith('ANA') and not self.is_article

    @property
    def serial_title(self):
        if self.is_article:
            # TODO: why don't we include always volume and collation
            # since they are always displayed together?
            return self.orig_serial_title
        else:
            # TODO: when is this shown???
            return join_available_values(' | ',
                                         self.orig_serial_title, self.volume_no)

    @property
    def conference(self):
        return join_available_values(' | ',
                                     self.conf_name, self.conf_no,
                                     self.conf_date, self.conf_place)

    @property
    def treaties(self):
        return self._all_references['treaties']

    @property
    def legislations(self):
        return self._all_references['legislations']

    @property
    def court_decisions(self):
        return self._all_references['court_decisions']

    @property
    def literatures(self):
        return self._all_references['literatures']

    @property
    def references(self):
        return self._all_references['references']
