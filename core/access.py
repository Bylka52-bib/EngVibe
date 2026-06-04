"""Доступ к курсам: активная подписка (тариф) или разовая покупка (CourseEnrollment)."""

from django.utils import timezone



from .models import Course, CourseEnrollment, UserSubscription

from .roles import can_manage_course, is_admin, is_teacher





def get_active_subscription(user):

    if not user.is_authenticated:

        return None

    now = timezone.now()

    return (

        UserSubscription.objects.filter(user=user, is_active=True, expires_at__gt=now)

        .select_related('plan')

        .prefetch_related('picked_courses')

        .order_by('-started_at')

        .first()

    )





def course_covered_by_active_subscription(user, course):

    """Курс входит в текущую активную подписку (без учёта разовой покупки)."""

    sub = get_active_subscription(user)

    if not sub:

        return False

    plan = sub.plan

    if plan.access_all:

        return True

    if plan.max_courses and plan.max_courses > 0:

        return sub.picked_courses.filter(course_id=course.pk).exists()

    return False





def user_has_course_access(user, course):

    """Доступ: преподаватель/админ курса, разовая покупка, или правила активной подписки."""

    if not user.is_authenticated:

        return False

    if can_manage_course(user, course):

        return True

    if CourseEnrollment.objects.filter(user=user, course=course).exists():

        return True

    sub = get_active_subscription(user)

    if not sub:

        return False

    plan = sub.plan

    if plan.access_all:

        return True

    if plan.max_courses and plan.max_courses > 0:

        return sub.picked_courses.filter(course_id=course.pk).exists()

    return False





def can_buy_course_separately(user, course):
    """
    Разовая покупка курса, к которому ещё нет доступа.
    С активной подпиской — любой неохваченный тарифом курс.
    Без подписки — любой курс, который ещё не куплен.
    """
    if not user.is_authenticated:
        return False
    if can_manage_course(user, course):
        return False
    if user_has_course_access(user, course):
        return False
    return True


def user_can_purchase_new_tariff(user):
    """Новый тариф можно оформить только после окончания текущей активной подписки."""
    if not user.is_authenticated:
        return True
    return get_active_subscription(user) is None


def tariff_purchase_block_message(user):
    sub = get_active_subscription(user)
    if not sub:
        return ''
    return (
        f'У вас уже активен тариф «{sub.plan.name}» до '
        f'{sub.expires_at.strftime("%d.%m.%Y")}. '
        f'Новый тариф можно оформить после окончания текущего.'
    )


def course_single_purchase_context(user, course):
    """Кнопка «Купить курс» на странице курса."""
    from django.urls import reverse
    from urllib.parse import quote

    if user and user.is_authenticated and (
        user_has_course_access(user, course) or can_manage_course(user, course)
    ):
        return {'show_buy': False, 'buy_url': '', 'buy_label': '', 'buy_hint': ''}

    checkout_url = reverse('core:course_checkout', kwargs={'slug': course.slug})
    label = f'Купить курс — {course.price} ₽'

    if not user or not user.is_authenticated:
        login_next = reverse('core:login') + '?next=' + quote(checkout_url, safe='')
        return {
            'show_buy': True,
            'buy_url': login_next,
            'buy_label': label,
            'buy_hint': 'Для оплаты нужно войти в аккаунт или зарегистрироваться.',
        }

    if can_buy_course_separately(user, course):
        sub = get_active_subscription(user)
        hint = ''
        if sub:
            hint = 'Курс не входит в ваш тарифный набор — можно купить отдельно.'
        return {
            'show_buy': True,
            'buy_url': checkout_url,
            'buy_label': label,
            'buy_hint': hint,
        }

    return {'show_buy': False, 'buy_url': '', 'buy_label': '', 'buy_hint': ''}


def can_buy_single_course_without_subscription(user, course):
    """Совместимость: то же, что can_buy_course_separately."""
    return can_buy_course_separately(user, course)





def get_accessible_courses_queryset(user):

    """Курсы для кабинета и прогресса: подписка + разовые покупки."""

    if not user.is_authenticated:

        return Course.objects.none()

    if is_admin(user) or is_teacher(user):

        return Course.objects.filter(published=True)



    enrolled_ids = list(CourseEnrollment.objects.filter(user=user).values_list('course_id', flat=True))

    sub = get_active_subscription(user)

    if not sub:

        if not enrolled_ids:

            return Course.objects.none()

        return Course.objects.filter(pk__in=enrolled_ids, published=True)



    if sub.plan.access_all:

        return Course.objects.filter(published=True)



    picked_ids = list(sub.picked_courses.values_list('course_id', flat=True))

    combined = set(picked_ids) | set(enrolled_ids)

    if not combined:

        return Course.objects.none()

    return Course.objects.filter(pk__in=combined, published=True)





def subscription_ui_flags(user):

    """Бейджи в шапке: PRO для премиум/годовой, метка базового тарифа."""

    sub = get_active_subscription(user)

    if not sub:

        return {'show_pro_badge': False, 'subscription_label': None, 'active_subscription': None}

    slug = sub.plan.slug

    if slug in ('premium', 'yearly'):

        return {'show_pro_badge': True, 'subscription_label': sub.plan.name, 'active_subscription': sub}

    if slug == 'basic':

        return {'show_pro_badge': False, 'subscription_label': sub.plan.name, 'active_subscription': sub}

    return {'show_pro_badge': False, 'subscription_label': sub.plan.name, 'active_subscription': sub}


