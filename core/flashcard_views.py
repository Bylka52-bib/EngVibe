import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .flashcards_utils import (
    all_card_ids,
    default_groups_with_progress,
    get_user_group,
    group_progress,
    mark_flashcard_answer,
    reset_group_progress,
    unlearned_card_ids,
    user_groups_with_progress,
)
from .forms import FlashcardForm, FlashcardGroupForm
from .models import Flashcard, FlashcardGroup


SESSION_KEY = 'flashcards_session'
RESULT_KEY = 'flashcards_result'


def _session_key(group_id):
    return f'{SESSION_KEY}_{group_id}'


def _result_key(group_id):
    return f'{RESULT_KEY}_{group_id}'


def _new_session(card_ids):
    ids = list(card_ids)
    random.shuffle(ids)
    return {
        'card_ids': ids,
        'index': 0,
        'known_count': 0,
        'unknown_count': 0,
        'reviewed': 0,
    }


@login_required
def flashcards_groups(request):
    return render(
        request,
        'core/flashcards_groups.html',
        {
            'default_groups': default_groups_with_progress(request.user),
            'user_groups': user_groups_with_progress(request.user),
        },
    )


@login_required
def flashcards_group_create(request):
    if request.method == 'POST':
        form = FlashcardGroupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            base_slug = slugify(name) or 'group'
            slug = base_slug
            n = 1
            while FlashcardGroup.objects.filter(owner=request.user, slug=slug).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            group = FlashcardGroup.objects.create(
                name=name,
                slug=slug,
                owner=request.user,
            )
            messages.success(request, f'Группа «{group.name}» создана. Добавьте карточки.')
            return redirect('core:flashcards_group_manage', slug=group.slug)
    else:
        form = FlashcardGroupForm()
    return render(
        request,
        'core/flashcards_group_form.html',
        {'form': form, 'title': 'Новая группа карточек'},
    )


def _user_owned_group(slug, user):
    group = get_user_group(slug, user)
    if not group or group.owner_id != user.id:
        return None
    return group


@login_required
def flashcards_group_manage(request, slug):
    group = _user_owned_group(slug, request.user)
    if not group:
        messages.error(request, 'Группа не найдена.')
        return redirect('core:flashcards_groups')

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_group':
            name = group.name
            group.delete()
            messages.success(request, f'Группа «{name}» удалена.')
            return redirect('core:flashcards_groups')

        card_form = FlashcardForm(request.POST)
        if card_form.is_valid():
            card = card_form.save(commit=False)
            card.group = group
            card.save()
            messages.success(request, f'Карточка «{card.word_en}» добавлена.')
            return redirect('core:flashcards_group_manage', slug=slug)
    else:
        card_form = FlashcardForm()

    return render(
        request,
        'core/flashcards_group_manage.html',
        {
            'group': group,
            'cards': group.cards.all(),
            'card_form': card_form,
            'has_cards': group.cards.exists(),
        },
    )


@login_required
def flashcards_play(request, slug):
    group = get_user_group(slug, request.user)
    if not group:
        messages.error(request, 'Группа не найдена.')
        return redirect('core:flashcards_groups')

    if request.GET.get('finished') == '1':
        rk = _result_key(group.id)
        session_data = request.session.pop(rk, None)
        request.session.modified = True
        progress = group_progress(request.user, group)
        return render(
            request,
            'core/flashcards_result.html',
            {
                'group': group,
                'session': session_data or {},
                'all_learned': progress['learned'] == progress['total'] and progress['total'] > 0,
                'can_restart_all': progress['total'] > 0,
            },
        )

    progress = group_progress(request.user, group)
    if progress['total'] == 0:
        messages.info(request, 'В этой группе пока нет карточек.')
        if group.owner_id == request.user.id:
            return redirect('core:flashcards_group_manage', slug=slug)
        return redirect('core:flashcards_groups')

    sk = _session_key(group.id)
    restart = request.GET.get('restart')

    if restart in ('all', '1'):
        reset_group_progress(request.user, group)
        card_ids = all_card_ids(group)
        request.session[sk] = _new_session(card_ids)
        request.session.modified = True
        progress = group_progress(request.user, group)
    elif sk not in request.session:
        card_ids = unlearned_card_ids(request.user, group)
        request.session[sk] = _new_session(card_ids)
        request.session.modified = True
        if not card_ids:
            return render(
                request,
                'core/flashcards_result.html',
                {
                    'group': group,
                    'session': {'reviewed': 0, 'known_count': 0, 'unknown_count': 0},
                    'all_learned': True,
                    'can_restart_all': True,
                },
            )

    session_data = request.session.get(sk, {})
    card_ids = session_data.get('card_ids', [])
    index = session_data.get('index', 0)

    if index >= len(card_ids):
        return render(
            request,
            'core/flashcards_result.html',
            {
                'group': group,
                'session': session_data,
                'all_learned': progress['learned'] == progress['total'],
                'can_restart_all': progress['total'] > 0,
            },
        )

    card = get_object_or_404(Flashcard, pk=card_ids[index], group=group)
    return render(
        request,
        'core/flashcards_play.html',
        {
            'group': group,
            'card': card,
            'progress': progress,
            'session': session_data,
            'current_num': index + 1,
            'session_total': len(card_ids),
            'can_restart_session': len(card_ids) > 0,
        },
    )


@login_required
@require_POST
def flashcards_answer(request, slug):
    group = get_user_group(slug, request.user)
    if not group:
        return JsonResponse({'error': 'Группа не найдена'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    card_id = payload.get('card_id')
    known = payload.get('known')
    if card_id is None or known is None:
        return JsonResponse({'error': 'Не указаны параметры'}, status=400)

    card = get_object_or_404(Flashcard, pk=card_id, group=group)
    mark_flashcard_answer(request.user, card, bool(known))

    sk = _session_key(group.id)
    session_data = request.session.get(sk, {})
    card_ids = session_data.get('card_ids', [])
    index = session_data.get('index', 0)

    if known:
        session_data['known_count'] = session_data.get('known_count', 0) + 1
    else:
        session_data['unknown_count'] = session_data.get('unknown_count', 0) + 1
    session_data['reviewed'] = session_data.get('reviewed', 0) + 1
    session_data['index'] = index + 1
    request.session[sk] = session_data
    request.session.modified = True

    progress = group_progress(request.user, group)
    next_index = session_data['index']

    if next_index >= len(card_ids):
        request.session[_result_key(group.id)] = session_data
        if sk in request.session:
            del request.session[sk]
        request.session.modified = True
        play_url = reverse('core:flashcards_play', kwargs={'slug': slug})
        return JsonResponse({
            'done': True,
            'redirect_url': f'{play_url}?finished=1',
            'progress': progress,
            'session': session_data,
        })

    next_card = Flashcard.objects.get(pk=card_ids[next_index])
    return JsonResponse({
        'done': False,
        'card': {
            'id': next_card.id,
            'word_en': next_card.word_en,
            'word_ru': next_card.word_ru,
        },
        'current_num': next_index + 1,
        'session_total': len(card_ids),
        'progress': progress,
    })
