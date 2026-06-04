def subscription_badge(request):
    return {}


def subscription_setup(request):
    return {
        'subscription_setup_pending': getattr(request, 'subscription_setup_pending', False),
    }