from datetime import datetime
import pysolr
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.conf import settings
from ecolex.search import search, get_document, PERPAGE, get_all_treaties, \
get_documents_by_field
from ecolex.forms import SearchForm, DOC_TYPE


class SearchView(TemplateView):
    template_name = 'homepage.html'

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)
        # Prepare query
        data = dict(self.request.GET)
        if 'q' in data:
            data['q'] = data['q'][0]
        data.setdefault('type', [])
        data.setdefault('tr_type', [])
        data.setdefault('tr_field', [])
        data.setdefault('tr_party', [])
        data.setdefault('tr_region', [])
        data.setdefault('tr_basin', [])
        data.setdefault('tr_subject', [])
        data.setdefault('tr_language', [])
        data.setdefault('keyword', [])
        data.setdefault('sortby', [''])
        for y in ('yearmin', 'yearmax', 'sortby'):
            data[y] = data[y][0] if y in data else None

        data.setdefault('dec_type', [])
        data.setdefault('dec_status', [])
        data.setdefault('dec_treaty', [])

        ctx['form'] = self.form = SearchForm(data=data)
        ctx['debug'] = settings.DEBUG
        ctx['text_suggestion'] = settings.TEXT_SUGGESTION
        self.query = self.form.data.get('q', '').strip() or '*'

        # Compute filters
        self.filters = {
            'type': data['type'] or dict(DOC_TYPE).keys(),
            'docKeyword': data['keyword'],
            'docDate': (data['yearmin'], data['yearmax']),
        }
        if 'treaty' in self.filters['type']:
            self.filters['trTypeOfText'] = data['tr_type']
            self.filters['trFieldOfApplication'] = data['tr_field']
            self.filters['partyCountry'] = data['tr_party']
            self.filters['trRegion'] = data['tr_region']
            self.filters['trBasin'] = data['tr_basin']
            self.filters['trSubject'] = data['tr_subject']
            self.filters['trLanguageOfDocument'] = data['tr_language']

        if 'decision' in self.filters['type']:
            self.filters['decType'] = data['dec_type']
            self.filters['decStatus'] = data['dec_status']
            self.filters['decTreatyId'] = data['dec_treaty']

        self.sortby = data['sortby']
        return ctx

    def update_form_choices(self, facets):
        """ After a query is run, there are new choices to be set.
        """

        def _extract(facet):
            values = (facets.get(facet) or {}).keys()
            return zip(values, values)

        self.form.fields['tr_type'].choices = _extract('trTypeOfText')
        self.form.fields['tr_field'].choices = _extract('trFieldOfApplication')
        self.form.fields['tr_party'].choices = _extract('partyCountry')
        self.form.fields['tr_region'].choices = _extract('trRegion')
        self.form.fields['tr_basin'].choices = _extract('trBasin')
        self.form.fields['tr_subject'].choices = _extract('trSubject')
        self.form.fields['tr_language'].choices = _extract('trLanguageOfDocument')
        self.form.fields['keyword'].choices = _extract('docKeyword')

        self.form.fields['dec_type'].choices = _extract('decType')
        self.form.fields['dec_status'].choices = _extract('decStatus')
        self.form.fields['dec_treaty'].choices = _extract('decTreatyId')


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
        pages_list = [p for p in
                     range(max(page - 2, 1), min(page + 2, results.pages()) + 1)]
        pages_urls = dict((page_no, _get_url(page_no)) for page_no in pages_list)

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
        fields = ['id', 'type', 'source', 'trTitleOfText', 'trJurisdiction',
                  'trPlaceOfAdoption', 'trDateOfText', 'trDateOfEntry',
                  'trDateOfModification', 'trPaperTitleOfText',
                  'trPaperTitleOfTextFr', 'trPaperTitleOfTextSp',
                  'trPaperTitleOfTextOther', 'trTitleOfTextShort',
                  'decTitleOfText', 'decStatus', 'decPublishDate',
                  'decUpdateDate', 'decNumber']
        results = search(self.query, filters=self.filters,
                         sortby=self.sortby, fields=fields)
        results.set_page(page)
        results.fetch()
        ctx['results'] = results
        ctx['facets'] = results.get_facets()
        ctx['stats_fields'] = results.get_field_stats()

        # a map of (treatyId -> treatyNames) for treaties which are referenced
        # by decisions in the current result set
        all_treaties = get_all_treaties()
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


class ResultDetails(SearchView):
    template_name = 'details.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetails, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'])
        if not results:
            raise Http404()
        context['document'] = results.first()
        context['results'] = results
        context['debug'] = settings.DEBUG
        context['page_type'] = 'homepage'
        if context['document'].type == 'decision':
            treaties = context['document'].solr.get('decTreatyId', [])
            all_treaties = get_all_treaties()
            context['all_treaties'] = [
                t for t in all_treaties if t.solr['trInformeaId'] in treaties
            ]
        if context['document'].type == 'treaty':
            ids = context['document'].get_references_ids_set()
            treaties_info = results.get_referred_treaties('trElisId', ids)
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
                            sort(key = lambda x: x.date(), reverse = True)

            if context['document'].informea_id():
                context['decisions'] = context['document'].get_decisions()
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
            x = meetings.get( decId, [] )
            x.append(decision)
            meetings[decId] = x
            meetingNames[decId] = decision.solr['decMeetingTitle'][0]
        context['meetings'] = meetings
        context['meetingNames'] = meetingNames
        return context

class ResultDetailsParticipants(SearchView):
    template_name = 'details_participants.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetailsParticipants, self).get_context_data(**kwargs)
        results = get_document(kwargs['id'])
        if not results:
            raise Http404()

        context['treaty'] = results.first()

        return context


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
