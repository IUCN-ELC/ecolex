
def global_config(request):
    from django.conf import settings
    expose_settings = [
        'STATIC_URL',
        'GA_CODE',
        'GA_ENABLED',
        'FACETS_PAGE_SIZE',
        'ECOLEX_CODE',
        'INFORMEA_CODE',
        'FAOLEX_CODE',
        'FAOLEX_CODE_2',
        'DEBUG',
    ]

    exposed_settings = {
        s: getattr(settings, s, None)
        for s in expose_settings
    }

    return {
        'settings': exposed_settings,
    }
