def set_iframe(request):
    if 'HTTP_REFERER' in request.META:
        return {
            'iframe': True,
        }
    return {}
