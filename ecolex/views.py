import logging
from urllib.parse import urlencode
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseForbidden, HttpResponseServerError
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django.views.generic.base import RedirectView

from datetime import datetime

from ecolex.definitions import FIELD_TO_FACET_MAPPING, SELECT_FACETS, STATIC_PAGES
from ecolex.export import get_exporter
from ecolex.legislation import harvest_file
from ecolex.models import StaticContent
from ecolex.mixins import ExportValidatorMixin
from ecolex.search import SearchMixin, get_documents_by_field
from ecolex.management.utils import EcolexSolr
from ecolex.management.definitions import UNLIMITED_ROWS_COUNT

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

        # A snippet of the about page should be included in Google search results
        about_content, created = StaticContent.objects.get_or_create(name='about')
        lang_code = get_language()
        about = getattr(about_content, 'body_{}'.format(lang_code))
        ctx['about'] = about

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
        obj = get_object_or_404(StaticContent, name=slug)
        lang_code = get_language()
        content = getattr(obj, 'body_' + lang_code, 'No translation for ' +
                          lang_code)
        ctx['content'] = content
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


class DetailPageRedirectView(RedirectView):

    doc_type_map = {
        'legislation': ('legId',),
        'treaty': ('trElisId',),
        'literature': ('litId',),
        'court_decision': ('cdOriginalId', 'cdLeoId',),
        'decision': ('decId',),
    }

    def get_redirect_url(self, *args, **kwargs):
        doc_id = kwargs.pop('doc_id', None)
        doc_type = kwargs.pop('doc_type', None)
        if not doc_id or not doc_type:
            return None
        search_fields = self.doc_type_map.get(doc_type)
        for f in search_fields:
            results = get_documents_by_field(f, [doc_id], rows=1)
            if results:
                break
        if not results:
            return None
        doc = [x for x in results][0]
        doc_details = doc_type + '_details'
        return reverse(doc_details, kwargs={'slug': doc.slug})

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)
        if url:
            return HttpResponseRedirect(url)
        else:
            raise Http404


class OldEcolexRedirectView(RedirectView):

    doc_type_map = {
        'documents': 'legislation',
        'treaties': 'treaty',
        'literature': 'literature',
        'courtdecisions': 'court_decision',
    }
    doc_id_map = {
        'legislation': 'legId',
        'treaty': 'trElisId',
        'literature': 'litId',
        'court_decision': 'cdOriginalId',
    }

    def get_redirect_url(self, doc_type, doc_id):
        doc_type = self.doc_type_map.get(doc_type)
        search_field = self.doc_id_map.get(doc_type)
        if not doc_type or not search_field:
            return reverse('results')
        results = get_documents_by_field(search_field, [doc_id], rows=1)
        if not results:
            return reverse('results')
        doc = [x for x in results][0]
        doc_details = doc_type + '_details'
        return reverse(doc_details, kwargs={'slug': doc.slug})

    def get(self, request, *args, **kwargs):
        doc_id = request.GET.get('id')
        doc_type = request.GET.get('index')
        if doc_id and doc_type:
            url = self.get_redirect_url(doc_type, doc_id)
            if url:
                return HttpResponseRedirect(url)
        else:
            return HttpResponseRedirect(reverse('results'))


class ExportView(View, ExportValidatorMixin):

    def clean_fields(self, fields):
        if not get_exporter(fields['format']):
            fields['format'] = 'json'

        try:
            fields['updated_after'] = (
                datetime
                .strptime(fields['updated_after'], '%Y%m%d')
                .strftime('%Y-%m-%dT%H:%M:%SZ')
            )
        except:
            fields['updated_after'] = None

        return fields

    def get_fields(self, request):
        fields = {
            'type': None,
            'slug': None,
            'format': 'json',
            'rows': UNLIMITED_ROWS_COUNT,
            'start': 0,
            'count': None,
            'download': None,
            'updated_after': None,
        }
        for field in request.GET:
            fields[field] = request.GET.get(field)

        return self.clean_fields(fields)

    def search_solr(self, fields):
        fq = ''
        fl = ''
        if fields['type']:
            key, value = 'type', fields['type']
            params = [
                'slug',
                'updatedDate',
                'docId',
            ]
            fl = ','.join(params)
            if fields['updated_after']:
                fq = 'updatedDate: [{} TO *]'.format(fields['updated_after'])
        elif fields['slug']:
            key, value = 'slug', fields['slug']
            fl = '*'
        else:
            key, value = '', ''

        solr = EcolexSolr()
        resp = solr.search_all(key, value, fq=fq, fl=fl, start=fields['start'],
                               rows=fields['rows'], sort='updatedDate desc')
        return resp

    def get(self, request, **kwargs):
        fields = self.get_fields(request)
        self.validate(fields)
        if self.errors:
            exporter = get_exporter(fields['format'])(self.errors)
            return exporter.get_response(fields['download'], status=400)

        resp = self.search_solr(fields)

        if not resp:
            resp = []
            exporter = get_exporter(fields['format'])(resp)
            return exporter.get_response(fields['download'], status=404)

        if fields['count'] == 'yes':
            resp = {'count': len(resp)}

        exporter = get_exporter(fields['format'])(resp)
        if fields['type'] and not fields['count']:
            exporter.attach_urls(request)
        return exporter.get_response(fields['download'])
