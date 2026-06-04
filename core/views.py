import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.views.decorators.http import require_POST

from .access import (
    can_buy_course_separately,
    course_covered_by_active_subscription,
    course_single_purchase_context,
    get_accessible_courses_queryset,
    get_active_subscription,
    tariff_purchase_block_message,
    user_has_course_access,
)
from .forms import (
    AnswerOptionForm,
    CourseForm,
    CourseTestForm,
    DemoPaymentForm,
    LessonForm,
    LoginForm,
    ProfileForm,
    QuestionForm,
    QuestionAnswersFormSet,
    ReviewForm,
    SignUpForm,
    UserRoleForm,
)
from .course_group_utils import (
    assign_subscription_courses_from_group,
    assign_subscription_individual_courses,
    groups_for_plan,
    plan_has_course_groups,
    subscription_needs_course_setup,
    subscription_setup_is_complete,
)
from .course_group_views import admin_course_groups, teacher_course_groups
from .models import (
    AnswerOption,
    Course,
    CourseEnrollment,
    CourseGroup,
    CourseTest,
    FAQ,
    Lesson,
    NewsletterSubscriber,
    Question,
    Review,
    TariffPlan,
    UserLessonProgress,
    UserProfile,
    UserSubscription,
    UserSubscriptionCourse,
    UserTestResult,
    WorkStage,
)
from .roles import can_manage_course, is_admin, is_student, is_teacher, is_teacher_or_admin


User = get_user_model()


def form_cancel_url(request, admin_tab='lessons'):
    if is_teacher(request.user) and not is_admin(request.user):
        return reverse('core:teacher_panel')
    return f'{reverse("core:admin_panel")}?tab={admin_tab}'


def _initial_rows_for_test_question_formset(course_test):
    """Данные для QuestionAnswersFormSet(initial=...) при редактировании теста."""
    rows = []
    for q in course_test.questions.prefetch_related('options').order_by('order', 'id'):
        opts = list(q.options.order_by('id'))[:4]
        texts = ['', '', '', '']
        correct_idx = 0
        for i, o in enumerate(opts):
            texts[i] = o.text
            if o.is_correct:
                correct_idx = i
        rows.append({
            'text': q.text,
            'order': q.order,
            'opt1': texts[0],
            'opt2': texts[1],
            'opt3': texts[2],
            'opt4': texts[3],
            'correct_choice': str(correct_idx + 1),
        })
    if not rows:
        rows.append({})
    return rows


def _replace_test_questions_from_formset(course_test, question_formset):
    """Удаляет старые вопросы теста и создаёт новые из валидированного formset (как при создании)."""
    course_test.questions.all().delete()
    seq = 1
    for qform in question_formset.forms:
        if qform.errors:
            continue
        cd = qform.cleaned_data
        if not cd or not (cd.get('text') or '').strip():
            continue
        order_val = cd.get('order')
        if order_val is None or order_val == '':
            order_val = seq
        question = Question.objects.create(
            test=course_test,
            text=cd['text'],
            order=int(order_val),
        )
        opts = cd['opts_stripped']
        ci = cd['correct_index']
        for i, opt_text in enumerate(opts):
            if not opt_text:
                continue
            AnswerOption.objects.create(
                question=question,
                text=opt_text[:400],
                is_correct=(i == ci),
            )
        seq += 1


def _safe_next(url):
    if not url or not isinstance(url, str):
        return reverse('core:profile')
    u = url.strip()
    if u.startswith('/') and not u.startswith('//'):
        return u
    return reverse('core:profile')


def home(request):
    courses = Course.objects.filter(published=True, is_premium=False)[:4]
    reviews = Review.objects.filter(is_published=True).select_related('user', 'user__profile')[:3]
    faqs = FAQ.objects.all()[:8]
    stages = WorkStage.objects.all()[:4]
    context = {
        'courses': courses,
        'reviews': reviews,
        'faqs': faqs,
        'stages': stages,
        'stats': {
            'courses_count': Course.objects.filter(published=True).count() or 50,
            'students_count': 10000,
            'rating': 4.9,
        },
    }
    return render(request, 'core/home.html', context)


def about_view(request):
    reviews = Review.objects.filter(is_published=True).select_related('user', 'user__profile')[:3]
    context = {
        'reviews': reviews,
        'stats': {
            'courses_count': Course.objects.filter(published=True).count() or 50,
            'rating': '4.9',
        },
    }
    return render(request, 'core/about.html', context)


def how_it_works_view(request):
    return render(request, 'core/how_it_works.html')


def social_soon_view(request):
    return render(request, 'core/social_soon.html')


def courses_list(request):
    courses = Course.objects.filter(published=True, is_premium=False)
    return render(request, 'core/courses_list.html', {'courses': courses})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, published=True)
    user = request.user if request.user.is_authenticated else None
    has_access = user_has_course_access(user, course) if user else False
    access_via_enrollment = False
    if user and has_access and not can_manage_course(user, course):
        access_via_enrollment = not course_covered_by_active_subscription(user, course)
    purchase = course_single_purchase_context(user, course)
    completed_lesson_ids = []
    tests = course.tests.none()
    if user and has_access:
        progress_qs = UserLessonProgress.objects.filter(user=user, lesson__course=course)
        completed_lesson_ids = [item.lesson_id for item in progress_qs if item.is_completed]
        tests = course.tests.prefetch_related('questions')
    return render(
        request,
        'core/course_detail.html',
        {
            'course': course,
            'has_access': has_access,
            'access_via_enrollment': access_via_enrollment,
            'purchase': purchase,
            'completed_lesson_ids': completed_lesson_ids,
            'tests': tests,
        },
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('core:profile')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Регистрация прошла успешно.')
        return redirect('core:profile')
    return render(request, 'core/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request.GET.get('next')))

    form = LoginForm(request.POST or None)
    next_candidate = (request.POST.get('next') if request.method == 'POST' else None) or request.GET.get('next')
    if request.method == 'POST' and form.is_valid():
        login(request, form.cleaned_data['user'])
        messages.success(request, 'Вы успешно вошли в аккаунт.')
        return redirect(_safe_next(next_candidate))
    return render(request, 'core/login.html', {'form': form, 'next_url': request.GET.get('next', '')})


def logout_confirm(request):
    if not request.user.is_authenticated:
        return redirect('core:home')
    return render(request, 'core/logout_confirm.html')


@require_POST
@login_required
def logout_do(request):
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта.')
    return redirect('core:home')


def newsletter_signup(request):
    if request.method != 'POST':
        return redirect('core:home')
    email = (request.POST.get('email') or '').strip().lower()
    if not email:
        messages.error(request, 'Укажите корректный email.')
        return redirect('core:home')
    try:
        NewsletterSubscriber.objects.create(email=email)
        messages.success(request, 'Спасибо, вы подписались на новости.')
    except IntegrityError:
        messages.info(request, 'Этот email уже в списке подписчиков.')
    return redirect('core:home')


@login_required
def profile_view(request):
    from .match_utils import user_match_stats
    from .sentence_utils import user_sentence_stats

    sentence_stats = user_sentence_stats(request.user)
    match_stats = user_match_stats(request.user)
    progress_rows = []
    if not is_admin(request.user) and not is_teacher(request.user):
        for course in get_accessible_courses_queryset(request.user):
            total_lessons = course.lessons.count()
            completed_lessons = UserLessonProgress.objects.filter(
                user=request.user,
                lesson__course=course,
                is_completed=True,
            ).count()
            progress_rows.append({
                'course': course,
                'completed_lessons': completed_lessons,
                'total_lessons': total_lessons,
                'percent': int((completed_lessons / total_lessons) * 100) if total_lessons else 0,
            })
    
    single_purchased_courses = Course.objects.filter(
        pk__in=CourseEnrollment.objects.filter(user=request.user).values_list('course_id', flat=True),
        published=True,
    )

    context = {
        'progress_rows': progress_rows,
        'single_purchased_courses': single_purchased_courses,
        'sentence_stats': sentence_stats,
        'match_stats': match_stats,
    }

    if is_admin(request.user):
        context['all_users'] = User.objects.prefetch_related('groups')
    elif is_teacher(request.user):
        context['teacher_courses'] = Course.objects.filter(teachers=request.user)
    
    return render(request, 'core/profile.html', context)


@login_required
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Профиль сохранён.')
        return redirect('core:profile')
    return render(request, 'core/profile_edit.html', {'form': form})


@user_passes_test(is_teacher_or_admin)
def course_create(request):
    form = CourseForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        course = form.save()
        if is_teacher(request.user) and not is_admin(request.user):
            course.teachers.add(request.user)
        messages.success(request, 'Курс успешно создан.')
        if is_teacher(request.user) and not is_admin(request.user):
            return redirect('core:teacher_panel')
        return redirect('core:courses')
    cancel = reverse('core:teacher_panel') if is_teacher(request.user) and not is_admin(request.user) else reverse('core:courses')
    return render(
        request,
        'core/course_form.html',
        {
            'form': form,
            'title': 'Добавить курс',
            'form_lead': 'Заполните карточку курса: уровень, описание, превью. После сохранения вы сможете добавить уроки и тесты.',
            'form_cancel_url': cancel,
        },
    )


@user_passes_test(is_teacher_or_admin)
def course_update(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if not can_manage_course(request.user, course):
        messages.error(request, 'У вас нет прав на редактирование этого курса.')
        return redirect('core:teacher_panel' if is_teacher(request.user) else 'core:courses')
    form = CourseForm(request.POST or None, request.FILES or None, instance=course, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Курс успешно обновлен.')
        return redirect('core:course_detail', slug=course.slug)
    cancel = reverse('core:teacher_panel') if is_teacher(request.user) and not is_admin(request.user) else reverse('core:courses')
    return render(
        request,
        'core/course_form.html',
        {
            'form': form,
            'title': 'Редактировать курс',
            'form_lead': 'Обновите данные курса и сохраните изменения.',
            'form_cancel_url': cancel,
        },
    )


@user_passes_test(is_teacher_or_admin)
def course_delete(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if not can_manage_course(request.user, course):
        messages.error(request, 'У вас нет прав на удаление этого курса.')
        return redirect('core:teacher_panel' if is_teacher(request.user) else 'core:courses')
    cancel = reverse('core:teacher_panel') if is_teacher(request.user) and not is_admin(request.user) else reverse('core:courses')
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'Курс «{title}» удалён.')
        return redirect(cancel)
    return render(
        request,
        'core/course_confirm_delete.html',
        {
            'course': course,
            'cancel_url': cancel,
        },
    )


@login_required
def lesson_detail(request, slug, lesson_id):
    course = get_object_or_404(Course, slug=slug, published=True)
    if not user_has_course_access(request.user, course):
        messages.warning(
            request,
            'Оформите тариф или купите этот курс разово — тогда откроются уроки и тесты.',
        )
        return redirect('core:course_detail', slug=course.slug)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    progress, _ = UserLessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    if request.method == 'POST':
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(update_fields=['is_completed', 'completed_at'])
        messages.success(request, 'Урок завершен.')
        return redirect('core:course_detail', slug=course.slug)
    return render(request, 'core/lesson_detail.html', {'course': course, 'lesson': lesson, 'progress': progress})


@login_required
def take_test(request, slug, test_id):
    course = get_object_or_404(Course, slug=slug, published=True)
    if not user_has_course_access(request.user, course):
        messages.warning(
            request,
            'Оформите тариф или купите этот курс разово — тогда откроются уроки и тесты.',
        )
        return redirect('core:course_detail', slug=course.slug)
    test = get_object_or_404(CourseTest.objects.prefetch_related('questions__options'), pk=test_id, course=course)
    attempts_count = UserTestResult.objects.filter(user=request.user, test=test).count()
    if attempts_count >= 3:
        messages.error(request, 'Вы уже прошли этот тест 3 раза. Доступ закрыт.')
        return redirect('core:course_detail', slug=course.slug)
    questions = list(test.questions.all())
    if request.method == 'POST':
        correct_answers = 0
        for question in questions:
            selected_id = request.POST.get(f'question_{question.id}')
            if not selected_id:
                continue
            try:
                selected_option = question.options.get(pk=selected_id)
            except AnswerOption.DoesNotExist:
                continue
            if selected_option.is_correct:
                correct_answers += 1

        total = len(questions)
        score = int((correct_answers / total) * 100) if total else 0
        UserTestResult.objects.create(
            user=request.user,
            test=test,
            score=score,
            total_questions=total,
            correct_answers=correct_answers,
        )
        messages.success(request, f'Тест завершен: {correct_answers}/{total} ({score}%).')
        return redirect('core:course_detail', slug=course.slug)
    return render(request, 'core/take_test.html', {'course': course, 'test': test, 'questions': questions})


def tariffs(request):
    active_sub = None
    if request.user.is_authenticated:
        active_sub = get_active_subscription(request.user)
    return render(
        request,
        'core/tariffs.html',
        {
            'plans': TariffPlan.objects.all(),
            'active_subscription': active_sub,
            'tariff_block_message': tariff_purchase_block_message(request.user)
            if request.user.is_authenticated
            else '',
        },
    )


@login_required
def course_checkout(request, slug):
    """Разовая покупка курса (демо), в том числе при активной подписке, если курса нет в тарифе."""
    course = get_object_or_404(Course, slug=slug, published=True)
    if user_has_course_access(request.user, course):
        messages.info(request, 'У вас уже есть доступ к этому курсу.')
        return redirect('core:course_detail', slug=course.slug)
    if not can_buy_course_separately(request.user, course):
        messages.warning(
            request,
            'Этот курс нельзя купить отдельно. Оформите тариф или выберите другой курс.',
        )
        return redirect('core:course_detail', slug=course.slug)
    payment_form = DemoPaymentForm(request.POST or None)
    if request.method == 'POST':
        if payment_form.is_valid():
            CourseEnrollment.objects.get_or_create(user=request.user, course=course)
            messages.success(request, 'Оплата прошла успешно (демо). Курс открыт.')
            return redirect('core:course_detail', slug=course.slug)
        messages.error(request, 'Проверьте данные карты и подтверждение оплаты.')
    return render(request, 'core/course_checkout.html', {'course': course, 'payment_form': payment_form})


def tariff_checkout(request, slug):
    plan = get_object_or_404(TariffPlan, slug=slug)
    if not request.user.is_authenticated:
        messages.info(request, 'Войдите в аккаунт, чтобы оформить подписку.')
        return redirect(f'{reverse("core:login")}?next={reverse("core:tariff_checkout", kwargs={"slug": slug})}')
    if get_active_subscription(request.user):
        messages.warning(request, tariff_purchase_block_message(request.user))
        return redirect('core:tariffs')
    payment_form = DemoPaymentForm(request.POST or None)
    if request.method == 'POST':
        if payment_form.is_valid():
            with transaction.atomic():
                UserSubscription.objects.filter(user=request.user, is_active=True).update(is_active=False)
                expires_at = timezone.now() + timedelta(days=plan.billing_days)
                sub = UserSubscription.objects.create(
                    user=request.user,
                    plan=plan,
                    expires_at=expires_at,
                    is_active=True,
                )
            messages.success(request, 'Оплата прошла успешно (демо). Подписка активирована.')
            if subscription_needs_course_setup(sub):
                return redirect('core:subscription_setup')
            return redirect('core:profile')
        messages.error(request, 'Проверьте данные карты и подтверждение оплаты.')
    return render(request, 'core/tariff_checkout.html', {'plan': plan, 'payment_form': payment_form})


@login_required
def subscription_setup(request):
    """После оплаты: группа курсов или свой набор (до max_courses по тарифу)."""
    sub = get_active_subscription(request.user)
    if not sub:
        messages.info(request, 'Сначала оформите подписку.')
        return redirect('core:tariffs')
    if sub.plan.access_all:
        return redirect('core:profile')

    plan = sub.plan
    groups = (
        groups_for_plan(plan)
        if plan_has_course_groups(plan)
        else CourseGroup.objects.none()
    )
    has_groups = groups.exists()
    max_n = plan.max_courses or 0
    catalog = Course.objects.filter(published=True)

    if not has_groups and not max_n:
        messages.info(request, 'Для вашего тарифа не требуется выбор курсов.')
        return redirect('core:profile')

    if subscription_setup_is_complete(sub):
        messages.info(request, 'Выбор курсов уже сделан при оформлении подписки и не может быть изменён.')
        return redirect('core:profile')

    if request.method == 'POST':
        mode = request.POST.get('choice_mode')
        if mode == 'group':
            if not has_groups:
                messages.error(request, 'Для этого тарифа нет групп курсов.')
                return redirect('core:subscription_setup')
            try:
                group_id = int(request.POST.get('group_id'))
            except (TypeError, ValueError):
                group_id = None
            group = groups.filter(pk=group_id).first() if group_id else None
            if not group:
                messages.error(request, 'Выберите группу из списка.')
                return redirect('core:subscription_setup')
            count = assign_subscription_courses_from_group(sub, group)
            if not count:
                messages.error(request, 'В группе нет опубликованных курсов.')
                return redirect('core:subscription_setup')
            messages.success(request, f'Группа «{group.name}»: доступ к {count} курсам.')
            return redirect('core:profile')

        if mode == 'courses':
            if not max_n:
                messages.error(request, 'Этот тариф не позволяет выбирать отдельные курсы.')
                return redirect('core:subscription_setup')
            raw_ids = request.POST.getlist('course_ids')
            if len(raw_ids) > max_n:
                messages.error(request, f'Можно выбрать не более {max_n} курсов.')
                return redirect('core:subscription_setup')
            ids = []
            for x in raw_ids:
                try:
                    ids.append(int(x))
                except (TypeError, ValueError):
                    continue
            ids = list(dict.fromkeys(ids))
            valid_ids = list(catalog.filter(pk__in=ids).values_list('pk', flat=True))[:max_n]
            if len(valid_ids) != max_n:
                messages.error(
                    request,
                    f'Нужно выбрать ровно {max_n} курса — не больше и не меньше.',
                )
                return redirect('core:subscription_setup')
            count = assign_subscription_individual_courses(sub, valid_ids)
            messages.success(request, f'Выбрано курсов: {count}. Доступ открыт.')
            return redirect('core:profile')

    return render(
        request,
        'core/subscription_setup.html',
        {
            'subscription': sub,
            'groups': groups,
            'has_groups': has_groups,
            'catalog': catalog,
            'max_n': max_n,
        },
    )


@login_required
def subscription_pick_group(request):
    return redirect('core:subscription_setup')


@login_required
def subscription_pick_courses(request):
    return redirect('core:subscription_setup')


def reviews_page(request):
    reviews = Review.objects.filter(is_published=True).select_related(
        'user',
        'user__profile',
    ).order_by('-created_at')
    form = ReviewForm(request.POST or None)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Только авторизованные пользователи могут оставлять отзывы.')
            return redirect(f'{reverse("core:login")}?next={reverse("core:reviews")}')
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.name = request.user.get_full_name() or request.user.username
            review.is_published = True
            review.save()
            messages.success(request, 'Спасибо за отзыв!')
            return redirect('core:reviews')
    return render(
        request,
        'core/reviews.html',
        {
            'reviews': reviews,
            'form': form,
            'reviews_batch_size': 3,
        },
    )


@user_passes_test(is_admin)
def admin_panel(request):
    tab = request.GET.get('tab', 'courses')
    author_filter = request.GET.get('author', '')
    group_authors = User.objects.filter(
        created_course_groups__isnull=False,
    ).distinct().order_by('username')
    author_filter_options = [('', 'Все')]
    author_filter_options.extend(
        (str(author.pk), author.username) for author in group_authors
    )
    context = {
        'tab': tab,
        'courses': Course.objects.all(),
        'lessons': Lesson.objects.select_related('course'),
        'tests': CourseTest.objects.select_related('course').annotate(questions_count=Count('questions')),
        'reviews': Review.objects.select_related('user', 'user__profile'),
        'users': User.objects.prefetch_related('groups'),
        'course_groups': admin_course_groups(author_filter or None),
        'group_authors': group_authors,
        'author_filter': author_filter,
        'author_filter_options': author_filter_options,
    }
    return render(request, 'core/admin_panel.html', context)


@user_passes_test(is_admin)
def user_role_update(request, user_id):
    managed_user = get_object_or_404(User, pk=user_id)
    current_group = managed_user.groups.first()
    form = UserRoleForm(request.POST or None, initial={'role': current_group.name if current_group else 'user_group'})
    if request.method == 'POST' and form.is_valid():
        role = form.cleaned_data['role']
        managed_user.groups.clear()
        group, _ = Group.objects.get_or_create(name=role)
        managed_user.groups.add(group)
        messages.success(request, f'Роль пользователя {managed_user.username} обновлена.')
        return redirect(f'{reverse("core:admin_panel")}?tab=users')
    return render(request, 'core/user_role_form.html', {'form': form, 'managed_user': managed_user})


@user_passes_test(is_teacher)
def teacher_panel(request):
    courses = (
        Course.objects.filter(teachers=request.user)
        .distinct()
        .prefetch_related(
            Prefetch('lessons', queryset=Lesson.objects.order_by('order', 'id')),
            Prefetch(
                'tests',
                queryset=CourseTest.objects.annotate(questions_count=Count('questions')).order_by('order', 'id'),
            ),
        )
        .order_by('title')
    )
    return render(
        request,
        'core/teacher_panel.html',
        {
            'courses': courses,
            'course_groups': teacher_course_groups(request.user),
        },
    )


@user_passes_test(is_teacher_or_admin)
def lesson_create(request):
    form = LessonForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        lesson = form.save(commit=False)
        if not can_manage_course(request.user, lesson.course):
            messages.error(request, 'Вы не можете управлять этим курсом.')
            return redirect(form_cancel_url(request, 'lessons'))
        lesson.save()
        messages.success(request, 'Урок создан.')
        return redirect(form_cancel_url(request, 'lessons'))
    return render(
        request,
        'core/lesson_form.html',
        {'form': form, 'title': 'Добавить урок', 'form_cancel_url': form_cancel_url(request, 'lessons')},
    )


@user_passes_test(is_teacher_or_admin)
@require_POST
def lesson_upload_image(request):
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': 'Файл не выбран'}, status=400)
    if upload.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'Размер файла не больше 5 МБ'}, status=400)
    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    if upload.content_type not in allowed_types:
        return JsonResponse({'error': 'Допустимы JPEG, PNG, GIF или WebP'}, status=400)
    ext = 'jpg'
    if '.' in upload.name:
        raw_ext = upload.name.rsplit('.', 1)[-1].lower()
        if raw_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            ext = raw_ext.replace('jpeg', 'jpg')
    filename = f'lessons/images/{uuid.uuid4().hex}.{ext}'
    saved_path = default_storage.save(filename, upload)
    url = f'{settings.MEDIA_URL}{saved_path}'.replace('\\', '/')
    return JsonResponse({'location': url})


@user_passes_test(is_teacher_or_admin)
def lesson_update(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if not can_manage_course(request.user, lesson.course):
        messages.error(request, 'Вы не можете управлять этим курсом.')
        return redirect(form_cancel_url(request, 'lessons'))
    form = LessonForm(request.POST or None, instance=lesson, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Урок обновлен.')
        return redirect(form_cancel_url(request, 'lessons'))
    return render(
        request,
        'core/lesson_form.html',
        {'form': form, 'title': 'Редактировать урок', 'form_cancel_url': form_cancel_url(request, 'lessons')},
    )


@user_passes_test(is_teacher_or_admin)
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if not can_manage_course(request.user, lesson.course):
        messages.error(request, 'Вы не можете управлять этим курсом.')
        return redirect(form_cancel_url(request, 'lessons'))
    cancel = form_cancel_url(request, 'lessons')
    if request.method == 'POST':
        title = lesson.title
        lesson.delete()
        messages.success(request, f'Урок «{title}» удалён.')
        return redirect(cancel)
    return render(
        request,
        'core/entity_confirm_delete.html',
        {
            'entity': lesson,
            'title': 'Удалить урок',
            'cancel_url': form_cancel_url(request, 'lessons'),
        },
    )


@user_passes_test(is_teacher_or_admin)
def test_create(request):
    if request.method == 'POST':
        test_form = CourseTestForm(request.POST, user=request.user)
        question_formset = QuestionAnswersFormSet(request.POST)
        if test_form.is_valid() and question_formset.is_valid():
            course_test = test_form.save(commit=False)
            if not can_manage_course(request.user, course_test.course):
                messages.error(request, 'Вы не можете управлять этим курсом.')
                return redirect(form_cancel_url(request, 'tests'))
            with transaction.atomic():
                course_test.save()
                _replace_test_questions_from_formset(course_test, question_formset)
            messages.success(request, 'Тест с вопросами и ответами сохранён.')
            return redirect(form_cancel_url(request, 'tests'))
    else:
        test_form = CourseTestForm(user=request.user)
        question_formset = QuestionAnswersFormSet()
    return render(
        request,
        'core/test_form.html',
        {
            'test_form': test_form,
            'question_formset': question_formset,
            'title': 'Новый тест',
            'form_cancel_url': form_cancel_url(request, 'tests'),
        },
    )


@user_passes_test(is_teacher_or_admin)
def test_update(request, test_id):
    course_test = get_object_or_404(
        CourseTest.objects.prefetch_related('questions__options'),
        pk=test_id,
    )
    if not can_manage_course(request.user, course_test.course):
        messages.error(request, 'Вы не можете управлять этим курсом.')
        return redirect(form_cancel_url(request, 'tests'))
    cancel = form_cancel_url(request, 'tests')
    if request.method == 'POST':
        test_form = CourseTestForm(request.POST, instance=course_test, user=request.user)
        question_formset = QuestionAnswersFormSet(request.POST)
        if test_form.is_valid() and question_formset.is_valid():
            updated = test_form.save(commit=False)
            if not can_manage_course(request.user, updated.course):
                messages.error(request, 'Вы не можете управлять этим курсом.')
                return redirect(cancel)
            with transaction.atomic():
                updated.save()
                _replace_test_questions_from_formset(updated, question_formset)
            messages.success(request, 'Тест обновлён.')
            return redirect(cancel)
    else:
        test_form = CourseTestForm(instance=course_test, user=request.user)
        initial_rows = _initial_rows_for_test_question_formset(course_test)
        question_formset = QuestionAnswersFormSet(initial=initial_rows)
    return render(
        request,
        'core/test_form.html',
        {
            'test_form': test_form,
            'question_formset': question_formset,
            'title': 'Редактировать тест',
            'form_cancel_url': cancel,
        },
    )


@user_passes_test(is_teacher_or_admin)
def test_delete(request, test_id):
    course_test = get_object_or_404(CourseTest, pk=test_id)
    if not can_manage_course(request.user, course_test.course):
        messages.error(request, 'Вы не можете управлять этим курсом.')
        return redirect(form_cancel_url(request, 'tests'))
    cancel = form_cancel_url(request, 'tests')
    if request.method == 'POST':
        title = course_test.title
        course_test.delete()
        messages.success(request, f'Тест «{title}» удалён.')
        return redirect(cancel)
    return render(
        request,
        'core/entity_confirm_delete.html',
        {
            'entity': course_test,
            'title': 'Удалить тест',
            'cancel_url': cancel,
        },
    )


@user_passes_test(is_teacher_or_admin)
def question_create(request):
    form = QuestionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        question = form.save(commit=False)
        if not can_manage_course(request.user, question.test.course):
            messages.error(request, 'Вы не можете управлять этим курсом.')
            return redirect('core:teacher_panel')
        question.save()
        messages.success(request, 'Вопрос добавлен.')
        return redirect('core:teacher_panel')
    return render(request, 'core/entity_form.html', {'form': form, 'title': 'Добавить вопрос', 'form_cancel_url': form_cancel_url(request, 'tests')})


@user_passes_test(is_teacher_or_admin)
def answer_create(request):
    form = AnswerOptionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        answer = form.save(commit=False)
        if not can_manage_course(request.user, answer.question.test.course):
            messages.error(request, 'Вы не можете управлять этим курсом.')
            return redirect('core:teacher_panel')
        answer.save()
        messages.success(request, 'Вариант ответа добавлен.')
        return redirect('core:teacher_panel')
    return render(request, 'core/entity_form.html', {'form': form, 'title': 'Добавить вариант ответа', 'form_cancel_url': form_cancel_url(request, 'tests')})
