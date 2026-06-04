import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .flashcards_utils import get_user_group
from .match_utils import (
    build_round_columns,
    default_groups_with_match_progress,
    mark_match_learned,
    match_group_progress,
    pick_round_card_ids,
    record_match_game_completed,
    user_match_stats,
)
from .models import Flashcard

SESSION_KEY = 'match_session'
RESULT_KEY = 'match_result'


def _session_key(group_id):
    return f'{SESSION_KEY}_{group_id}'


def _result_key(group_id):
    return f'{RESULT_KEY}_{group_id}'


def _new_session(card_ids):
    return {
        'card_ids': list(card_ids),
        'matched_ids': [],
        'wrong_attempts': 0,
        'correct_count': 0,
        'started_at': timezone.now().isoformat(),
    }


def _format_duration(seconds):
    if seconds is None:
        return None
    if seconds >= 60:
        minutes, secs = divmod(seconds, 60)
        return f'{minutes} мин. {secs} сек.'
    return f'{seconds} сек.'


def _session_duration_seconds(session_data):
    started = session_data.get('started_at')
    if not started:
        return None
    try:
        start_dt = datetime.fromisoformat(started)
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
    except (TypeError, ValueError):
        return None
    return max(0, int((timezone.now() - start_dt).total_seconds()))


@login_required
def match_levels(request):
    return render(
        request,
        'core/match_levels.html',
        {
            'levels': default_groups_with_match_progress(request.user),
            'stats': user_match_stats(request.user),
        },
    )


@login_required
def match_play(request, slug):
    group = get_user_group(slug, request.user)
    if not group:
        messages.error(request, 'Уровень не найден.')
        return redirect('core:match_levels')

    if request.GET.get('finished') == '1':
        rk = _result_key(group.id)
        session_data = request.session.pop(rk, None)
        request.session.modified = True
        duration_sec = _session_duration_seconds(session_data or {})
        return render(
            request,
            'core/match_result.html',
            {
                'group': group,
                'session': session_data or {},
                'duration_label': _format_duration(duration_sec),
                'progress': match_group_progress(request.user, group),
            },
        )

    progress = match_group_progress(request.user, group)
    if progress['total'] < 4:
        messages.info(
            request,
            f'Для игры нужно минимум 4 слова в группе «{group.name}». Сейчас: {progress["total"]}.',
        )
        return redirect('core:match_levels')

    sk = _session_key(group.id)
    if request.GET.get('restart') == '1' or sk not in request.session:
        card_ids = pick_round_card_ids(request.user, group)
        if len(card_ids) < 4:
            messages.info(request, 'Недостаточно слов для нового раунда.')
            return redirect('core:match_levels')
        request.session[sk] = _new_session(card_ids)
        request.session.modified = True

    session_data = request.session.get(sk, {})
    card_ids = session_data.get('card_ids', [])
    matched_ids = set(session_data.get('matched_ids', []))

    if not card_ids:
        return redirect('core:match_levels')

    if len(matched_ids) >= len(card_ids):
        request.session[_result_key(group.id)] = session_data
        if group.level:
            record_match_game_completed(request.user, group.level)
        if sk in request.session:
            del request.session[sk]
        request.session.modified = True
        play_url = reverse('core:match_play', kwargs={'slug': slug})
        return redirect(f'{play_url}?finished=1')

    en_cards, ru_cards = build_round_columns(card_ids)
    for card in en_cards:
        card['matched'] = card['id'] in matched_ids
    for card in ru_cards:
        card['matched'] = card['id'] in matched_ids

    return render(
        request,
        'core/match_play.html',
        {
            'group': group,
            'en_cards': en_cards,
            'ru_cards': ru_cards,
            'progress': progress,
            'session': session_data,
            'remaining': len(card_ids) - len(matched_ids),
            'total_pairs': len(card_ids),
        },
    )


@login_required
@require_POST
def match_check(request, slug):
    group = get_user_group(slug, request.user)
    if not group:
        return JsonResponse({'error': 'Уровень не найден'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    en_id = payload.get('en_id')
    ru_id = payload.get('ru_id')
    if en_id is None or ru_id is None:
        return JsonResponse({'error': 'Не указаны слова'}, status=400)

    try:
        en_id = int(en_id)
        ru_id = int(ru_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Неверные идентификаторы'}, status=400)

    sk = _session_key(group.id)
    session_data = request.session.get(sk)
    if not session_data:
        return JsonResponse({'error': 'Сессия игры не найдена'}, status=400)

    card_ids = session_data.get('card_ids', [])
    matched_ids = session_data.get('matched_ids', [])

    if en_id not in card_ids or ru_id not in card_ids:
        return JsonResponse({'error': 'Слово не из этого раунда'}, status=400)

    if en_id in matched_ids or ru_id in matched_ids:
        return JsonResponse({'error': 'Пара уже сопоставлена'}, status=400)

    correct = en_id == ru_id

    if not correct:
        session_data['wrong_attempts'] = session_data.get('wrong_attempts', 0) + 1
        request.session[sk] = session_data
        request.session.modified = True
        return JsonResponse({
            'correct': False,
            'remaining': len(card_ids) - len(matched_ids),
        })

    flashcard = get_object_or_404(Flashcard, pk=en_id, group=group)
    mark_match_learned(request.user, flashcard)
    matched_ids.append(en_id)
    session_data['matched_ids'] = matched_ids
    session_data['correct_count'] = session_data.get('correct_count', 0) + 1
    request.session[sk] = session_data
    request.session.modified = True

    remaining = len(card_ids) - len(matched_ids)
    progress = match_group_progress(request.user, group)

    if remaining == 0:
        if group.level:
            record_match_game_completed(request.user, group.level)
        request.session[_result_key(group.id)] = session_data
        if sk in request.session:
            del request.session[sk]
        request.session.modified = True
        play_url = reverse('core:match_play', kwargs={'slug': slug})
        return JsonResponse({
            'correct': True,
            'done': True,
            'remaining': 0,
            'progress': progress,
            'redirect_url': f'{play_url}?finished=1',
        })

    return JsonResponse({
        'correct': True,
        'done': False,
        'remaining': remaining,
        'progress': progress,
        'matched_id': en_id,
    })
