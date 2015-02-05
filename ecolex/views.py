from datetime import datetime
import pysolr
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.generic import TemplateView
from ecolex.search import search, get_document, PERPAGE
from ecolex.forms import SearchForm, DOC_TYPE


class SearchView(TemplateView):
    template_name = 'search.html'

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)
        # Prepare query
        data = dict(self.request.GET)
        if 'q' in data:
            data['q'] = data['q'][0]
        data.setdefault('type', dict(DOC_TYPE).keys())
        data.setdefault('tr_type', [])
        data.setdefault('tr_field', [])
        data.setdefault('tr_party', [])
        data.setdefault('tr_subject', [])
        data.setdefault('keyword', [])

        data.setdefault('dec_type', [])
        data.setdefault('dec_status', [])
        data.setdefault('dec_treaty', [])

        ctx['form'] = self.form = SearchForm(data=data)
        self.query = self.form.data.get('q', '').strip() or '*'

        # Compute filters
        self.filters = {
            'type': data['type'],
            'trKeyword': data['keyword'],
        }
        if 'treaty' in data['type']:  # specific filters
            self.filters['trTypeOfText'] = data['tr_type']
            self.filters['trFieldOfApplication'] = data['tr_field']
            self.filters['partyCountry'] = data['tr_party']
            self.filters['trSubject'] = data['tr_subject']

        if 'decision' in data['type']:
            self.filters['decType'] = data['dec_type']
            self.filters['decStatus'] = data['dec_status']
            self.filters['decTreatyId'] = data['dec_treaty']
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
        self.form.fields['keyword'].choices = _extract('trKeyword')

        self.form.fields['dec_type'].choices = _extract('decType')
        self.form.fields['dec_status'].choices = _extract('decStatus')
        self.form.fields['dec_treaty'].choices = _extract('decTreatyId')



class SearchViewWithResults(SearchView):
    template_name = 'list_results.html'

    def page_details(self, page, results, request):
        get_query = request.GET.copy()
        get_query.pop(page, None)

        def _get_url(page):
            get_query['page'] = page
            return get_query.urlencode()

        return {
            'number': page,
            'pages': results.pages,
            'next_url': _get_url(page + 1),
            'prev_url': _get_url(page - 1),
        }

    def get(self, request, **kwargs):
        page = int(self.request.GET.get('page', 1))
        ctx = self.get_context_data(**kwargs)
        results = search(self.query, filters=self.filters)
        results.set_page(page)
        results.fetch()
        ctx['results'] = results
        ctx['facets'] = results.get_facets()
        ctx['page'] = self.page_details(page, results, request)
        self.update_form_choices(ctx['facets'])

        return render(request, 'list_results.html', ctx)


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
        context['document'] = get_document(kwargs['id'])
        return context
