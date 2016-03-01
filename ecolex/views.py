from django.conf import settings
from django.http import Http404, HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from urllib.parse import urlencode
import logging
from ecolex.legislation import harvest_file

from ecolex.search import (
    search, get_document, get_documents_by_field, get_treaty_by_informea_id,
    SearchMixin,
)
from ecolex.definitions import (
    FIELD_TO_FACET_MAPPING, SELECT_FACETS
)


logger = logging.getLogger(__name__)


class SearchView(TemplateView, SearchMixin):
    template_name = 'homepage.html'

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)

        # Prepare query
        self._prepare(self.request.GET)

        ctx['form'] = self.form # set by _prepare above
        ctx['debug'] = settings.DEBUG
        ctx['text_suggestion'] = settings.TEXT_SUGGESTION
        ctx['query'] = urlencode(self.request.GET)

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
        results = self.search()

        results.set_page(page)
        results.fetch()
        ctx['results'] = results
        ctx['facets'] = results.get_facets()
        ctx['stats_fields'] = results.get_field_stats()
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
        results = self.search()

        facets = results.get_facets()
        data = {}
        for k, v in SELECT_FACETS.items():
            if k not in facets:
                continue
            show_empty = True if len(results) == 0 else False
            context = {
                'facet': facets[k],
                'form_field': ctx['form'][v],
                'show_empty': show_empty
            }
            html = render_to_string('bits/fancy_select.html', context)
            data[v] = html
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
        ctx['results'] = get_documents_by_field('partyCountry_en',
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

        results = get_document(document_id=kwargs['id'], query=self.query,
                               hl_details=True)
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

    def _sort_references(self, doc, fields, treaty_references, treaties):
        references = {}
        for field in fields:
            treaties_list = treaty_references.get(field, [])
            if treaties_list and any(treaties_list):
                label = doc.REFERENCE_FIELDS.get(field)
                references.setdefault(label, [])
                references[label].extend([t for t in treaties
                                          if t.solr.get('trElisId', -1)
                                          in treaties_list])
                references[label].sort(key=lambda x: x.date(),
                                       reverse=True)
                if len(references[label]) == 0:
                    references.pop(label)
        return references

    def get_context_data(self, **kwargs):
        context = super(TreatyDetails, self).get_context_data(**kwargs)

        doc = context['document']
        treaty_references = doc.references()
        treaty_ids = [v for x in treaty_references.values() for v in x]
        treaties = context['results'].get_referred_treaties('trElisId',
                                                            treaty_ids)
        if treaty_references:
            context['direct_links'] = self._sort_references(
                doc, doc.DIRECT_LINKS, treaty_references, treaties)
            context['back_links'] = self._sort_references(
                doc, doc.BACK_LINKS, treaty_references, treaties)

        if doc.informea_id():
            context['decisions'] = doc.get_decisions()
        context['literatures'] = doc.get_literatures()
        context['court_decisions'] = doc.get_court_decisions()

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
        logger = logging.getLogger('legislation_import')
        #for key,val in request.META.items():
        #    logger.debug('Header %s = %s' % (key,val))
        key = request.META.get('HTTP_API_KEY', None)
        api_key = getattr(settings, 'FAOLEX_API_KEY')
        if not key or key != api_key:
            logger.error('Bad API KEY!')
            return HttpResponseForbidden('Bad API key')
        return super(FaoFeedView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        logger = logging.getLogger('legislation_import')
        #logger.debug(request.body)
        legislation_file = request.FILES.get('file', None)
        if not legislation_file:
            logger.error('No attached file!')
            response = 'You have to attach an XML file!'
        else:
            try:
                response = harvest_file(legislation_file)
                logger.info(response)
                data = {
                    'message': response
                }
                return JsonResponse(data)
            except:
                logger.exception('Error harvesting file')
        return HttpResponseServerError('Internal server error during harvesting')

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


class DesignPlayground(TemplateView):
    template_name = 'playground.html'
