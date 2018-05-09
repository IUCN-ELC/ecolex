from django.conf import settings
from raven.contrib.django.raven_compat.models import sentry_exception_handler


class SentryForwardedForMiddleware(object):
    def process_exception(self, request, exception):
        request.META['REMOTE_ADDR'] = (
                request.META.get('HTTP_X_FORWARDED_FOR') or
                request.META['REMOTE_ADDR'])
        sentry_exception_handler(request=request)


class CacheControlMiddleware(object):
    def process_response(self, request, response):
        if settings.DEBUG:
            response['cache-control'] = 'no-cache, max-age=0'
        return response
