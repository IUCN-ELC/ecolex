import logging
from urllib.parse import urlencode
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseForbidden, HttpResponseServerError
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django.views.generic.base import RedirectView

from ecolex.legislation import harvest_file
from ecolex.definitions import FIELD_TO_FACET_MAPPING, SELECT_FACETS, STATIC_PAGES
from ecolex.search import (
    SearchMixin, get_documents_by_field,
)


logger = logging.getLogger(__name__)


class SearchView(TemplateView, SearchMixin):
    template_name = 'homepage.html'

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)

        # Prepare query
        self._prepare(self.request.GET)

        ctx['form'] = self.form  # set by _prepare above
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
            if k == 'xdate':
                continue
            self.form.fields[k].choices = _extract(v)


class Homepage(SearchView):
    def get_context_data(self, **kwargs):
        ctx = super(Homepage, self).get_context_data(**kwargs)
        ctx['page_type'] = 'homepage'
        return ctx


class PageNotFoundView(SearchView):
    template_name = '404.html'

    def get(self, request, *args, **kwargs):
        ctx = super(PageNotFoundView, self).get_context_data(**kwargs)
        return self.render_to_response(ctx, status=404)


class InternalErrorView(SearchView):
    template_name = '500.html'

    def get(self, request, *args, **kwargs):
        ctx = super(InternalErrorView, self).get_context_data(**kwargs)
        return self.render_to_response(ctx, status=500)


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

        # fetch one extra facet result, to let the frontend know
        # if it should use ajax for the next pages
        results = self.search(facets_page_size=settings.FACETS_PAGE_SIZE + 1)

        results.set_page(page)
        results.fetch()
        ctx['results'] = results

        facets = results.get_facets()

        # hack the (select) facets to have "pretty" keys.
        # TODO: move this logic into Queryset.get_facets().
        #       multilinguality could live there too!
        #       (or even better, make the names pretty in schema...)
        for old_key, new_key in SELECT_FACETS.items():
            if old_key not in facets:
                continue
            # also convert them to the api serializer format
            # (or not, handle it client-side for now)
            # facets[new_key] = SearchFacetSerializer.convert_results(
            #    facets.pop(old_key))

            # also hack them into a {results: [], more: bool} dict,
            # accounting for that odd extra-result
            f_data = facets.pop(old_key)
            more = False

            if len(f_data) > settings.FACETS_PAGE_SIZE:
                more = True
                f_data.popitem()

            facets[new_key] = {
                'results': f_data,
                'more': more,
            }

        ctx['facets'] = facets
        ctx['stats_fields'] = results.get_field_stats()
        ctx['page'] = self.page_details(page, results)
        self.update_form_choices(ctx['facets'])
        return ctx

    def get(self, request, **kwargs):
        ctx = self.get_context_data(**kwargs)
        return render(request, 'list_results.html', ctx)


class PageView(SearchView):

    def get(self, request, **kwargs):
        slug = kwargs.pop('slug', '')
        if slug not in STATIC_PAGES:
            raise Http404()
        ctx = self.get_context_data()
        ctx['page_slug'] = slug
        return render(request, 'pages/' + slug + '.html', ctx)


class FaoFeedView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        logger = logging.getLogger('legislation_import')
        # for key,val in request.META.items():
        #    logger.debug('Header %s = %s' % (key,val))
        key = request.META.get('HTTP_API_KEY', None)
        api_key = getattr(settings, 'FAOLEX_API_KEY')
        if not key or key != api_key:
            logger.error('Bad API KEY!')
            return HttpResponseForbidden('Bad API key')
        return super(FaoFeedView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        logger = logging.getLogger('legislation_import')
        # logger.debug(request.body)
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


class LegislationRedirectView(RedirectView):

    doc_type_map = {
        'legislation': 'legId',
        'treaty': 'trElisId',
        'literature': 'litId',
    }

    def get_redirect_url(self, *args, **kwargs):
        doc_id = kwargs.pop('doc_id', None)
        doc_type = kwargs.pop('doc_type', None)
        if not doc_id or not doc_type:
            return None
        search_field = self.doc_type_map.get(doc_type)
        results = get_documents_by_field(search_field, [doc_id], rows=1)
        if not results:
            return None
        leg = [x for x in results][0]
        doc_details = doc_type + '_details'
        return reverse(doc_details, kwargs={'slug': leg.solr.get('slug')})

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)
        if url:
            return HttpResponseRedirect(url)
        else:
            return HttpResponse('Arguments missing or document is not indexed')
