from django.conf import settings


class CacheControlMiddleware(object):
    def process_response(self, request, response):
        if settings.DEBUG:
            response['cache-control'] = 'no-cache, max-age=0'
        return response
