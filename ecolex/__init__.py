
def global_config(request):
    from django.conf import settings

    return {'GA_CODE': settings.GA_CODE}
