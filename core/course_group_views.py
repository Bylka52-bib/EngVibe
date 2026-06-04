from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from .course_group_utils import available_courses_for_group_form
from .forms import CourseGroupForm
from .models import CourseGroup
from .roles import can_manage_course_group, is_admin, is_teacher_or_admin


def _panel_redirect(user):
    if is_admin(user):
        return reverse('core:admin_panel') + '?tab=course_groups'
    return reverse('core:teacher_panel')


@user_passes_test(is_teacher_or_admin)
def course_group_create(request):
    form = CourseGroupForm(
        request.POST or None,
        user=request.user,
        is_admin_user=is_admin(request.user),
    )
    if request.method == 'POST' and form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        base_slug = slugify(group.name) or 'group'
        slug = base_slug
        n = 1
        while CourseGroup.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{n}'
            n += 1
        group.slug = slug
        group.save()
        form.save_m2m()
        messages.success(request, f'Группа «{group.name}» создана.')
        return redirect(_panel_redirect(request.user))
    return render(
        request,
        'core/course_group_form.html',
        {
            'form': form,
            'title': 'Создать группу курсов',
            'cancel_url': _panel_redirect(request.user),
        },
    )


@user_passes_test(is_teacher_or_admin)
def course_group_update(request, slug):
    group = get_object_or_404(CourseGroup, slug=slug)
    if not can_manage_course_group(request.user, group):
        messages.error(request, 'Вы не можете редактировать эту группу.')
        return redirect(_panel_redirect(request.user))

    form = CourseGroupForm(
        request.POST or None,
        instance=group,
        user=request.user,
        is_admin_user=is_admin(request.user),
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Группа «{group.name}» обновлена.')
        return redirect(_panel_redirect(request.user))
    return render(
        request,
        'core/course_group_form.html',
        {
            'form': form,
            'title': 'Редактировать группу курсов',
            'group': group,
            'cancel_url': _panel_redirect(request.user),
        },
    )


@user_passes_test(is_teacher_or_admin)
def course_group_delete(request, slug):
    group = get_object_or_404(CourseGroup, slug=slug)
    if not can_manage_course_group(request.user, group):
        messages.error(request, 'Вы не можете удалить эту группу.')
        return redirect(_panel_redirect(request.user))

    cancel_url = _panel_redirect(request.user)
    if request.method == 'POST':
        title = group.name
        group.delete()
        messages.success(request, f'Группа «{title}» удалена.')
        return redirect(cancel_url)
    return render(
        request,
        'core/entity_confirm_delete.html',
        {
            'entity': group,
            'title': 'Удалить группу курсов',
            'cancel_url': cancel_url,
        },
    )


def teacher_course_groups(user):
    return (
        CourseGroup.objects.filter(created_by=user)
        .select_related('tariff_plan', 'created_by')
        .annotate(course_count=Count('courses'))
        .order_by('order', 'name')
    )


def admin_course_groups(author_id=None):
    qs = (
        CourseGroup.objects.select_related('tariff_plan', 'created_by')
        .annotate(course_count=Count('courses'))
        .order_by('order', 'name')
    )
    if author_id:
        try:
            qs = qs.filter(created_by_id=int(author_id))
        except (TypeError, ValueError):
            pass
    return qs
