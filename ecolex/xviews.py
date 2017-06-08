import math
from collections import OrderedDict
from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.views.generic import TemplateView, View
from django.utils.functional import cached_property
from django.utils.translation import get_language

from .xforms import SearchForm
from .xsearch import Queryer, Searcher, SearchResponse, DEFAULT_INTERFACE as si
from ecolex.management import definitions


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

        form.set_facet_data(response.facets)

        ctx['results'] = response
        ctx['facets'] = response.facets
        ctx['stats'] = response.stats
        ctx['suggestions'] = (response.suggestions if settings.TEXT_SUGGESTION
                              else [])
        ctx['pages'] = self.get_page_details(page, response.count)
        ctx['page_type'] = 'search'
        ctx['page_slug'] = None

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

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        document = context['document']
        if hasattr(self, 'doc_type') and document.type != self.doc_type:
            url = reverse('{}_details'.format(document.type),
                          kwargs={'slug': document.slug})
            return HttpResponseRedirect(url)
        return super().get(request, *args, **kwargs)


class DecisionDetails(DetailsView):
    template_name = 'details/decision.html'
    doc_type = definitions.COP_DECISION


class TreatyDetails(DetailsView):
    template_name = 'details/treaty.html'
    doc_type = definitions.TREATY

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        leg_implemented = len(getattr(ctx['document'],
                                      'legislations_implemented_by', []))
        leg_cited = len(getattr(ctx['document'], 'legislations_cited_by', []))
        if leg_implemented or leg_cited:
            ctx['document'].legislation_count = leg_implemented + leg_cited

        return ctx


class LiteratureDetails(DetailsView):
    template_name = 'details/literature.html'
    doc_type = definitions.LITERATURE


class CourtDecisionDetails(DetailsView):
    template_name = 'details/court_decision.html'
    doc_type = definitions.COURT_DECISION


class LegislationDetails(DetailsView):
    template_name = 'details/legislation.html'
    doc_type = definitions.LEGISLATION


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

        if self.related_type == 'legislation':
            return ctx

        remote_field, local_field = doc.OTHER_REFERENCES[self.related_type]
        try:
            value = getattr(doc, local_field)
        except AttributeError:
            raise Http404()

        page = self.request.GET.get('xpage', 1)
        page = int(page) if page != 'None' else 1

        lookups = {doc._resolve_field(remote_field, self.related_type): value}

        response = self.fetch_results(lookups, page)

        ctx['related_objects'] = response.results
        ctx['pages'] = self.get_page_details(page, response.count)

        return ctx


class RelatedLegislation(DetailsView):
    related_type = 'legislation'
    template_name = 'details_legislations.html'

    def fetch_results(self, lookups):
        queryer = Queryer({}, language=get_language())
        response = queryer.findany(date_sort=False, page_size=10000, **lookups)
        return response

    def get_context_data(self, **kwargs):
        ctx = super(RelatedLegislation, self).get_context_data(**kwargs)
        doc = ctx['document']
        for remote_field, local_field in doc.LEGISLATION_REFERENCES.items():
            try:
                value = getattr(doc, local_field)
            except AttributeError:
                raise Http404()
            lookups = {
                doc._resolve_field(remote_field, definitions.LEGISLATION): value,
            }
            response = self.fetch_results(lookups)
            ctx[remote_field] = response.results
        return ctx


class RelatedLiterature(RelatedObjectsView):
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
            # 'group.ngroups': True, # we could use this in template
            # 'group.format': 'simple', # this is implied by group.main
        }

        # TODO: make the sorting variable?
        response = queryer.findany(page=page, date_sort=False,
                                   options=options, **lookups)

        return response


@method_decorator(login_required, name='dispatch')
class DocumentDeleteSearch(SearchViewMixin, TemplateView):

    template_name = 'delete_search.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        url = self.request.GET.get('url', None)
        if url:
            elements = url.split('/')
            slug = elements[5] if len(elements) > 5 else None
            if slug:
                data = {'type': ''}
                queryer = Queryer(data, language=get_language())
                try:
                    record = queryer.get(slug=slug)
                except ObjectDoesNotExist:
                    record = None

            ctx['slug'] = slug
            ctx['record'] = record
        return ctx

    def post(self, request, *args, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = request.POST.get('confirm_delete', None)
        if slug:
            si.delete_by_query(query=si.Q(slug=slug))
            si.commit()
            ctx['message_level'] = 'success'
            ctx['message'] = 'Successfully deleted record!'
        else:
            ctx['message_level'] = 'warning'
            ctx['message'] = 'Slug not found!'
        return self.render_to_response(ctx)


@method_decorator(login_required, name='dispatch')
class DocumentDelete(View):

    def get_redirect_url(self):
        query = urlencode(self.request.GET)
        return '{}?{}'.format(reverse('results'), query)

    def post(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        if slug:
            si.delete_by_query(query=si.Q(slug=slug))
            si.commit()
            messages.success(request, 'Record deleted successfully!')
        else:
            messages.error(request, "Record slug couldn't be found!")
        url = self.get_redirect_url()
        return HttpResponseRedirect(url)


class PageNotFound(SearchViewMixin, TemplateView):
    template_name = '404.html'

    def get(self, request, *args, **kwargs):
        ctx = super(PageNotFound, self).get_context_data(**kwargs)
        return self.render_to_response(ctx, status=404)


class InternalError(SearchViewMixin, TemplateView):
    template_name = '500.html'

    def get(self, request, *args, **kwargs):
        ctx = super(InternalError, self).get_context_data(**kwargs)
        return self.render_to_response(ctx, status=500)
