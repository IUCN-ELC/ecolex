import math
from collections import OrderedDict
from urllib.parse import urlencode
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http import Http404
from django.views.generic import TemplateView
from django.utils.functional import cached_property
from django.utils.translation import get_language
from .xforms import SearchForm
from .xsearch import Queryer, Searcher, SearchResponse


class HomepageView(TemplateView):
    template_name = 'homepage.html'

homepage_view = HomepageView.as_view()


class SearchViewMixin(object):
    @cached_property
    def form(self):
        data = self.request.GET.copy()
        for k in data.keys():
            if k.endswith('[]'):
                v = data.pop(k)
                data.setlist(k[:-2], v)
        return SearchForm(data)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['query'] = urlencode(self.request.GET)
        return ctx


class PagedViewMixin(object):
    def _get_page_url(self, page=None):
        raise NotImplementedError()

    def get_page_details(self, current, result_count, page_size=None):
        if page_size is None:
            page_size = settings.SEARCH_PAGE_SIZE

        page_count = math.ceil(result_count / page_size)

        if page_count <= 1:
            _url = self._get_page_url()
            return {
                'number': 1,
                'count': 1,
                'list': [1],
                'urls': {1: _url},
                'next_url': None,
                'prev_url': None,
                'first_url': _url,
                'last_url': _url,
            }

        _get_url = self._get_page_url

        pages = OrderedDict((p, _get_url(p))
                            for p in range(max(current - 2, 1),
                                           min(current + 2, page_count) + 1))

        return {
            'number': current,
            'count': page_count,
            'list': pages.keys(),
            'urls': pages,

            'next_url': current < page_count and _get_url(current + 1) or None,
            'prev_url': current > 1 and _get_url(current - 1) or None,

            'first_url': _get_url(1),
            'last_url': _get_url(page_count),
        }


class SearchResults(SearchViewMixin, PagedViewMixin, TemplateView):
    template_name = 'list_results.html'

    def get(self, request, *args, **kwargs):
        if not self.form.changed_data:
            return homepage_view(request, *args, **kwargs)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = self.form

        if not form.is_valid():
            response = SearchResponse()
            page = 1
        else:
            data = form.cleaned_data.copy()

            page = data.pop('page')
            sortby = data.pop('sortby')

            date_sort = {
                form.SORT_DEFAULT: None,
                form.SORT_ASC: True,
                form.SORT_DESC: False,
            }[sortby]

            searcher = Searcher(data, language=get_language())
            response = searcher.search(page=page, date_sort=date_sort)

        ctx['results'] = response
        ctx['facets'] = response.facets
        ctx['stats'] = response.stats
        ctx['suggestions'] = (response.suggestions if settings.TEXT_SUGGESTION
                              else [])
        ctx['pages'] = self.get_page_details(page, response.count)

        return ctx

    def _get_page_url(self, page=None):
        if page is None:
            return self.form.urlencoded()
        else:
            return self.form.urlencoded(page=page)


class DetailsView(SearchViewMixin, TemplateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = kwargs['slug']

        form = self.form

        if not form.is_valid():
            raise Http404()

        data = form.cleaned_data.copy()

        queryer = Queryer(data, language=get_language())

        try:
            result = queryer.get(slug=slug)
        except ObjectDoesNotExist:
            raise Http404()
        except MultipleObjectsReturned:
            # TODO. this is either data or code error.
            raise

        ctx['document'] = result

        return ctx


class DecisionDetails(DetailsView):
    template_name = 'details/decision.html'


class TreatyDetails(DetailsView):
    template_name = 'details/treaty.html'


class LiteratureDetails(DetailsView):
    template_name = 'details/literature.html'


class CourtDecisionDetails(DetailsView):
    template_name = 'details/court_decision.html'


class LegislationDetails(DetailsView):
    template_name = 'details/legislation.html'


# TODO: it's wasteful to fetch all treaty details for this view
class TreatyParticipants(TreatyDetails):
    template_name = 'details_participants.html'


# this extends DetailsView just because we need access to the parent object,
# which is wasteful. TODO: write a view that fetches only the needed fields.
class RelatedObjectsView(PagedViewMixin, DetailsView):
    # this is looked up in the object's OTHER_REFERENCES
    related_type = None

    @cached_property
    def __query_dict(self):
        return self.request.GET.copy()

    def _get_page_url(self, page=None):
        query_dict = self.__query_dict
        try:
            del query_dict['xpage']
        except KeyError:
            pass

        if page != 1:
            query_dict['xpage'] = page

        return query_dict.urlencode()

    def fetch_results(self, lookups, page):
        queryer = Queryer({}, language=get_language())
        # TODO: make the sorting variable?
        response = queryer.findany(page=page, date_sort=False, **lookups)

        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = ctx['document']

        remote_field, local_field = doc.OTHER_REFERENCES[self.related_type]
        try:
            value = getattr(doc, local_field)
        except AttributeError:
            raise Http404()

        page = int(self.request.GET.get('xpage', 1))

        lookups = {doc._resolve_field(remote_field, self.related_type): value}

        response = self.fetch_results(lookups, page)

        ctx['related_objects'] = response.results
        ctx['pages'] = self.get_page_details(page, response.count)

        return ctx


class RelatedLiteratures(RelatedObjectsView):
    related_type = 'literature'
    template_name = 'details_literatures.html'


class RelatedCourtDecisions(RelatedObjectsView):
    related_type = 'court_decision'
    template_name = 'details_court_decisions.html'


class RelatedDecisions(RelatedObjectsView):
    related_type = 'decision'
    template_name = 'details_decisions.html'

    def fetch_results(self, lookups, page):
        queryer = Queryer({}, language=get_language())

        # TODO: this is really ugly
        options = {
            'group': True,
            'group.field': 'decMeetingId_group',
            'group.sort': 'decNumber_sort asc',
            'group.limit': 1000,
            'group.main': True,
            #'group.ngroups': True, # we could use this in template
            #'group.format': 'simple', # this is implied by group.main
        }

        # TODO: make the sorting variable?
        response = queryer.findany(page=page, date_sort=False,
                                   options=options, **lookups)

        return response
