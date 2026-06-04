from django.contrib import messages
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .access import get_active_subscription
from .course_group_utils import subscription_needs_course_setup, subscription_setup_is_complete
from .roles import is_teacher_or_admin

_PATH_PREFIXES = ('/static/', '/media/', '/admin/')

_ALLOWED_URL_NAMES = frozenset({
    'core:subscription_setup',
    'core:subscription_pick_group',
    'core:subscription_pick_courses',
    'core:logout',
    'core:logout_do',
})


def _resolved_url_name(path):
    try:
        match = resolve(path)
    except Resolver404:
        return None
    if match.url_name is None:
        return None
    if match.namespace:
        return f'{match.namespace}:{match.url_name}'
    return match.url_name


def user_needs_subscription_setup(user):
    if not user or not user.is_authenticated or is_teacher_or_admin(user):
        return False
    sub = get_active_subscription(user)
    if not sub:
        return False
    if not subscription_needs_course_setup(sub):
        return False
    return not subscription_setup_is_complete(sub)


class SubscriptionSetupRequiredMiddleware:
    """Пока не выбраны курсы/группа после оплаты — только страница настройки и выход."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pending = user_needs_subscription_setup(getattr(request, 'user', None))
        request.subscription_setup_pending = pending

        if pending and not any(request.path.startswith(p) for p in _PATH_PREFIXES):
            url_name = _resolved_url_name(request.path)
            if url_name not in _ALLOWED_URL_NAMES:
                messages.warning(
                    request,
                    'Завершите выбор курсов или группы — без этого подписка не активируется полностью.',
                )
                return redirect('core:subscription_setup')

        return self.get_response(request)
