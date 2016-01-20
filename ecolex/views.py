from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View
from django.conf import settings
import logging
from urllib.parse import urlencode

from contrib.import_legislation_fao import harvest_file
from ecolex.search import (
    search, get_document, get_documents_by_field, get_treaty_by_informea_id
)
from ecolex.forms import SearchForm
from ecolex.definitions import (
    DOC_TYPE, DOC_TYPE_FILTER_MAPPING, FIELD_TO_FACET_MAPPING, SOLR_FIELDS,
    OPERATION_FIELD_MAPPING, SELECT_FACETS
)

from uuid import uuid4


logger = logging.getLogger(__name__)


class SearchView(TemplateView):
    template_name = 'homepage.html'

    def _set_form_defaults(self, data):
        exclude_fields = ['q', 'sortby', 'yearmin', 'yearmax']
        fields = [x for x in SearchForm.base_fields if x not in exclude_fields]
        for field in fields:
            data.setdefault(field, [])
        if 'q' in data:
            data['q'] = data['q'][0]

        data.setdefault('sortby', [''])
        for y in ('yearmin', 'yearmax', 'sortby'):
            data[y] = data[y][0] if y in data else None
        return data

    def _set_filters(self, data):
        filters = {
            'type': data['type'] or dict(DOC_TYPE).keys(),
            'docKeyword': data['keyword'],
            'docSubject': data['subject'],
            'docCountry': data['country'],
            'docRegion': data['region'],
            'docLanguage': data['language'],
            'docDate': (data['yearmin'], data['yearmax']),
        }
        for doc_type in filters['type']:
            mapping = DOC_TYPE_FILTER_MAPPING[doc_type]
            for k, v in mapping.items():
                filters[k] = data[v]

        for field in OPERATION_FIELD_MAPPING.keys():
            field_name = OPERATION_FIELD_MAPPING[field]
            facet_name = FIELD_TO_FACET_MAPPING[field_name]
            if not data[field] and facet_name in filters:
                values = filters.pop(facet_name)
                facet_name = '{!ex=%s}' % str(uuid4())[:8] + facet_name
                filters[facet_name] = values
        return filters

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)
        # Prepare query
        data = self._set_form_defaults(dict(self.request.GET))

        ctx['form'] = self.form = SearchForm(data=data)
        ctx['debug'] = settings.DEBUG
        ctx['text_suggestion'] = settings.TEXT_SUGGESTION
        ctx['query'] = urlencode(self.request.GET)

        self.query = self.form.data.get('q', '').strip() or '*'
        # Compute filters
        self.filters = self._set_filters(data)
        self.sortby = data['sortby']

        return ctx

    def update_form_choices(self, facets):
        """ After a query is run, there are new choices to be set.
        """

        def _extract(facet):
            values = (facets.get(facet) or {}).keys()
            return zip(values, values)

        for k, v in FIELD_TO_FACET_MAPPING.items():
            self.form.fields[k].choices = _extract(v)


class Homepage(SearchView):
    def get_context_data(self, **kwargs):
        ctx = super(Homepage, self).get_context_data(**kwargs)
        ctx['page_type'] = 'homepage'
        return ctx


class SearchResults(SearchView):
    template_name = 'list_results.html'

    def page_details(self, page, results):
        def _get_url(page):
            get_query['page'] = page
            return get_query.urlencode()

        get_query = self.request.GET.copy()
        get_query.pop(page, None)
        pages_list = [p for p in range(max(page - 2, 1),
                                       min(page + 2, results.pages()) + 1)]
        pages_urls = dict((page_no, _get_url(page_no))
                          for page_no in pages_list)

        return {
            'number': page,
            'no_pages': results.pages,
            'pages_list': pages_list,
            'pages_urls': pages_urls,
            'next_url': _get_url(page + 1),
            'prev_url': _get_url(page - 1),
            'first_url': _get_url(1),
            'last_url': _get_url(results.pages()),
        }

    def get_context_data(self, **kwargs):
        ctx = super(SearchResults, self).get_context_data(**kwargs)
        page = int(self.request.GET.get('page', 1))
        fields = SOLR_FIELDS
        results = search(self.query, filters=self.filters,
                         sortby=self.sortby, fields=fields)
        results.set_page(page)
        results.fetch()
        ctx['results'] = results
        ctx['facets'] = results.get_facets()
        ctx['stats_fields'] = results.get_field_stats()

        # a map of (treatyId -> treatyNames) for treaties which are referenced
        # by decisions in the current result set
        types = self.request.GET.getlist('type', [])
        if 'decision' in types or types == []:
            all_treaties = results.get_facet_treaty_names()
            ctx['dec_treaty_names'] = {
                t.informea_id(): t for t in all_treaties
            }
        ctx['page'] = self.page_details(page, results)
        self.update_form_choices(ctx['facets'])
        return ctx

    def get(self, request, **kwargs):
        ctx = self.get_context_data(**kwargs)
        return render(request, 'list_results.html', ctx)


class SearchResultsAjax(SearchResults):

    def get(self, request, **kwargs):
        ctx = self.get_context_data(**kwargs)
        main = render_to_string('results_main.html', ctx)
        sidebar = render_to_string('results_sidebar.html', ctx)
        search_form_inputs = render_to_string('bits/hidden_form.html', ctx)
        return JsonResponse(dict(main=main, sidebar=sidebar,
                                 form_inputs=search_form_inputs))


class SelectFacetsAjax(SearchView):

    def get(self, request, **kwargs):
        ctx = super(SelectFacetsAjax, self).get_context_data(**kwargs)
        fields = SOLR_FIELDS
        results = search(self.query, filters=self.filters, sortby=self.sortby,
                         fields=fields)
        facets = results.get_facets()
        data = {}
        for k, v in SELECT_FACETS.items():
            if k not in facets:
                continue
            context = {
                'facet': facets[k],
                'form_field': ctx['form'][v]
            }
            data[v] = render_to_string('bits/fancy_select.html', context)

        return JsonResponse(data)


class DecMeetingView(SearchView):
    template_name = 'decision_meeting_details.html'

    def get_context_data(self, **kwargs):
        ctx = super(DecMeetingView, self).get_context_data(**kwargs)
        ctx['results'] = get_documents_by_field('decMeetingId',
                                                [kwargs['id']],
                                                1000000)  # get all results
        return ctx


class TreatyParticipantView(SearchView):
    template_name = 'treaty_participant_details.html'

    def get_context_data(self, **kwargs):
        ctx = super(TreatyParticipantView, self).get_context_data(**kwargs)
        ctx['results'] = get_documents_by_field('partyCountry',
                                                [kwargs['id']],
                                                1000000)  # get all results
        return ctx


class PageView(SearchView):

    def get(self, request, **kwargs):
        slug = kwargs.pop('slug', '')
        PAGES = ('about', 'privacy', 'agreement', 'acknowledgements')
        if slug not in PAGES:
            raise Http404()
        ctx = self.get_context_data()
        ctx['page_slug'] = slug
        return render(request, 'pages/' + slug + '.html', ctx)


class DetailsView(SearchView):

    def get_context_data(self, **kwargs):
        context = super(DetailsView, self).get_context_data(**kwargs)

        results = get_document(document_id=kwargs['id'], query=self.query)
        if not results:
            raise Http404()
        context['document'] = results.first()
        context['results'] = results
        context['debug'] = settings.DEBUG
        context['page_type'] = 'homepage'

        return context


class DecisionDetails(DetailsView):

    template_name = 'details/decision.html'

    def get_context_data(self, **kwargs):
        context = super(DecisionDetails, self).get_context_data(**kwargs)
        treaty_id = context['document'].solr.get('decTreatyId', None)

        if treaty_id:
            treaty = get_treaty_by_informea_id(treaty_id)
            context['treaty'] = treaty

        return context


class TreatyDetails(DetailsView):

    template_name = 'details/treaty.html'

    def get_context_data(self, **kwargs):
        context = super(TreatyDetails, self).get_context_data(**kwargs)

        ids = context['document'].get_references_ids_set()
        treaties_info = context['results'].get_referred_treaties('trElisId',
                                                                 ids)
        references_mapping = context['document'].references()
        if references_mapping:
            context['references'] = {}
            for label, treaties_list in references_mapping.items():
                if treaties_list and any(treaties_list):
                    context['references'].setdefault(label, [])
                    context['references'][label].\
                        extend([t for t in treaties_info
                                if t.solr.get('trElisId', -1) in treaties_list])
                    context['references'][label].\
                        sort(key=lambda x: x.date(), reverse=True)
        if context['document'].informea_id():
            context['decisions'] = context['document'].get_decisions()
        context['literatures'] = context['document'].get_literatures()
        context['court_decisions'] = context['document'].get_court_decisions()

        return context


class LiteratureDetails(DetailsView):

    template_name = 'details/literature.html'

    def get_context_data(self, **kwargs):
        context = super(LiteratureDetails, self).get_context_data(**kwargs)
        document = context['document']
        reference_ids = document.get_references_ids_dict()
        references_to = document.get_references_from_ids(reference_ids)
        references_from = document.get_references_from()
        context['references_to'] = references_to
        context['references_from'] = references_from
        return context


class CourtDecisionDetails(DetailsView):

    template_name = 'details/court_decision.html'

    def get_context_data(self, **kwargs):
        context = super(CourtDecisionDetails, self).get_context_data(**kwargs)
        references = context['document'].get_references()
        referenced_by = context['document'].get_referenced_by()
        context['references'] = references
        context['referenced_by'] = referenced_by
        return context


class LegislationDetails(DetailsView):

    template_name = 'details/legislation.html'

    def get_context_data(self, **kwargs):
        context = super(LegislationDetails, self).get_context_data(**kwargs)
        leg = context['document']
        context['leg_references'] = leg.get_legislation_references()
        context['leg_back_references'] = leg.get_legislation_back_references()
        return context


class ResultDetailsDecisions(SearchView):
    template_name = 'details_decisions.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetailsDecisions, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'])
        if not results.count():
            raise Http404()

        meetings = {}
        meetingNames = {}
        context['treaty'] = results.first()
        context['page_type'] = 'homepage'

        for decision in context['treaty'].get_decisions():
            decId = decision.solr['decMeetingId'][0]
            x = meetings.get(decId, [])
            x.append(decision)
            meetings[decId] = x
            if 'decMeetingTitle' in decision.solr:
                meetingNames[decId] = decision.solr['decMeetingTitle'][0]
        context['meetings'] = meetings
        context['meetingNames'] = meetingNames
        return context


class ResultDetailsLiteratures(SearchView):

    template_name = 'details_literatures.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetailsLiteratures, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'])
        if not results.count():
            raise Http404

        context['treaty'] = results.first()
        context['page_type'] = 'homepage'
        context['literatures'] = context['treaty'].get_literatures()
        return context


class ResultDetailsCourtDecisions(SearchView):

    template_name = 'details_court_decisions.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetailsCourtDecisions, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'])
        if not results.count():
            raise Http404

        context['treaty'] = results.first()
        context['page_type'] = 'homepage'
        context['court_decisions'] = context['treaty'].get_court_decisions()
        return context


class ResultDetailsParticipants(SearchView):
    template_name = 'details_participants.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetailsParticipants, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'], self.query)
        if not results:
            raise Http404()

        context['treaty'] = results.first()

        return context


class FaoFeedView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        key = request.META.get('HTTP_API_KEY', None)
        api_key = getattr(settings, 'FAOLEX_API_KEY')
        if not key or key != api_key:
            logger.error('No API KEY!')
            raise Http404
        return super(FaoFeedView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        legislation_file = request.FILES.get('file', None)
        if legislation_file:
            response = harvest_file(legislation_file, logger)
            logger.info(response)
        else:
            logger.error('No attached file!')
            response = 'You have to attach an XML file!'
        data = {
            'message': response
        }
        return JsonResponse(data)


def debug(request):
    import subprocess

    last_update = subprocess.check_output(
        ['git', 'show', '--pretty=medium', '--format="%aD %cn"']).decode()
    last_update = last_update and last_update.split('\n')[0]
    last_update = last_update.replace('\"', '')

    data = {
        'debug': settings.DEBUG,
        'endpoint': settings.SOLR_URI,
        'last_update': last_update,
    }
    return JsonResponse(data)
