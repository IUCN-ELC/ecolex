from datetime import datetime
import pysolr
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.conf import settings
from ecolex.search import search, get_document, PERPAGE
from ecolex.forms import SearchForm, DOC_TYPE
from django.conf import settings


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
        data.setdefault('tr_subject', [])
        data.setdefault('keyword', [])
        data.setdefault('sortby', [''])
        for y in ('yearmin', 'yearmax', 'sortby'):
            data[y] = data[y][0] if y in data else None

        data.setdefault('dec_type', [])
        data.setdefault('dec_status', [])
        data.setdefault('dec_treaty', [])

        ctx['form'] = self.form = SearchForm(data=data)
        ctx['debug'] = settings.DEBUG
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
            self.filters['trSubject'] = data['tr_subject']

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
        self.form.fields['tr_subject'].choices = _extract('trSubject')
        self.form.fields['keyword'].choices = _extract('docKeyword')

        self.form.fields['dec_type'].choices = _extract('decType')
        self.form.fields['dec_status'].choices = _extract('decStatus')
        self.form.fields['dec_treaty'].choices = _extract('decTreatyId')


class SearchResults(SearchView):
    template_name = 'list_results.html'

    def page_details(self, page, results):
        get_query = self.request.GET.copy()
        get_query.pop(page, None)

        def _get_url(page):
            get_query['page'] = page
            return get_query.urlencode()

        return {
            'number': page,
            'pages': results.pages,
            'next_url': _get_url(page + 1),
            'prev_url': _get_url(page - 1),
            'first_url': _get_url(1),
            'last_url': _get_url(results.pages()),
        }

    def get_context_data(self, **kwargs):
        ctx = super(SearchResults, self).get_context_data(**kwargs)
        page = int(self.request.GET.get('page', 1))
        results = search(self.query, filters=self.filters, sortby=self.sortby)
        results.set_page(page)
        results.fetch()
        ctx['results'] = results
        ctx['facets'] = results.get_facets()
        ctx['stats_fields'] = results.get_field_stats()

        # a map of (treatyId -> treatyNames) for treaties which are referenced
        # by decisions in the current result set
        ctx['dec_treaty_names'] = results.get_facet_treaty_names()

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
        return JsonResponse(dict(main=main, sidebar=sidebar))


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
        context['dec_treaty_names'] = results.get_facet_treaty_names()
        if context['document'].type == 'treaty':
            ids = context['document'].get_references_ids_set()
            references_info = results.get_references_info('trElisId', ids)
            context['references_display_names'] = results.\
                get_references_display_names(references_info)
            context['references_solr_ids'] = results.\
                get_references_solr_ids(references_info)
            context['references_titles'] = results.\
                get_references_titles(references_info)
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
