
def global_config(request):
    from django.conf import settings
    expose_settings = [
        'GA_CODE',
        'FACETS_PAGE_SIZE',
        'DEBUG',
    ]

    exposed_settings = {
        s: getattr(settings, s, None)
        for s in expose_settings
    }

    return {
        'settings': exposed_settings,
    }
