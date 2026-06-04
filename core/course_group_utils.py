from django.db.models import Count

from .models import Course, CourseGroup


def plan_has_course_groups(plan):
    return CourseGroup.objects.filter(tariff_plan=plan).exists()


def groups_for_plan(plan):
    return (
        CourseGroup.objects.filter(tariff_plan=plan)
        .select_related('created_by', 'tariff_plan')
        .annotate(course_count=Count('courses'))
        .order_by('order', 'name')
    )


def subscription_needs_course_setup(sub):
    """Нужно выбрать группу или отдельные курсы (не тариф «все курсы»)."""
    if not sub or sub.plan.access_all:
        return False
    if sub.plan.max_courses and sub.plan.max_courses > 0:
        return True
    return plan_has_course_groups(sub.plan)


def subscription_setup_is_complete(sub):
    if not sub:
        return False
    if sub.plan.access_all:
        return True
    return sub.setup_completed


def assign_subscription_individual_courses(subscription, course_ids):
    from .models import UserSubscriptionCourse

    UserSubscriptionCourse.objects.filter(subscription=subscription).delete()
    for cid in course_ids:
        UserSubscriptionCourse.objects.create(subscription=subscription, course_id=cid)
    subscription.course_group = None
    subscription.setup_completed = True
    subscription.save(update_fields=['course_group', 'setup_completed'])
    return len(course_ids)


def assign_subscription_courses_from_group(subscription, group):
    """Все опубликованные курсы группы → подписка пользователя."""
    from .models import UserSubscriptionCourse

    course_ids = list(
        group.courses.filter(published=True).values_list('pk', flat=True)
    )
    UserSubscriptionCourse.objects.filter(subscription=subscription).delete()
    for cid in course_ids:
        UserSubscriptionCourse.objects.create(subscription=subscription, course_id=cid)
    subscription.course_group = group
    subscription.setup_completed = True
    subscription.save(update_fields=['course_group', 'setup_completed'])
    return len(course_ids)


def available_courses_for_group_form(user, *, is_admin_user):
    qs = Course.objects.filter(published=True).order_by('title')
    if is_admin_user:
        return qs
    return qs.filter(teachers=user).distinct()
