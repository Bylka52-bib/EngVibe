import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import SentenceGameTask
from .sentence_utils import (
    all_levels_with_progress,
    all_task_ids,
    get_level_label,
    is_valid_level,
    level_progress,
    mark_task_solved,
    reset_level_progress,
    shuffled_words,
    unsolved_task_ids,
    user_sentence_stats,
    words_match,
)

SESSION_KEY = 'sentence_session'
RESULT_KEY = 'sentence_result'


def _session_key(level):
    return f'{SESSION_KEY}_{level}'


def _result_key(level):
    return f'{RESULT_KEY}_{level}'


def _new_session(task_ids):
    ids = list(task_ids)
    random.shuffle(ids)
    return {
        'task_ids': ids,
        'index': 0,
        'correct_count': 0,
        'attempts': 0,
    }


@login_required
def sentence_builder_levels(request):
    return render(
        request,
        'core/sentence_builder_levels.html',
        {
            'levels': all_levels_with_progress(request.user),
            'stats': user_sentence_stats(request.user),
        },
    )


@login_required
def sentence_builder_play(request, level):
    if not is_valid_level(level):
        messages.error(request, 'Уровень не найден.')
        return redirect('core:sentence_builder_levels')

    if request.GET.get('finished') == '1':
        rk = _result_key(level)
        session_data = request.session.pop(rk, None)
        request.session.modified = True
        return render(
            request,
            'core/sentence_builder_result.html',
            {
                'level': level,
                'level_label': get_level_label(level),
                'session': session_data or {},
                'progress': level_progress(request.user, level),
            },
        )

    progress = level_progress(request.user, level)
    if progress['total'] == 0:
        messages.info(request, 'Задания для этого уровня скоро появятся.')
        return redirect('core:sentence_builder_levels')

    sk = _session_key(level)
    restart = request.GET.get('restart')

    if restart in ('all', '1'):
        reset_level_progress(request.user, level)
        task_ids = all_task_ids(level)
        request.session[sk] = _new_session(task_ids)
        request.session.modified = True
        progress = level_progress(request.user, level)
    elif sk not in request.session:
        task_ids = unsolved_task_ids(request.user, level)
        request.session[sk] = _new_session(task_ids)
        request.session.modified = True
        if not task_ids:
            return render(
                request,
                'core/sentence_builder_result.html',
                {
                    'level': level,
                    'level_label': get_level_label(level),
                    'session': {'correct_count': 0, 'attempts': 0},
                    'progress': progress,
                    'all_solved': True,
                },
            )

    session_data = request.session.get(sk, {})
    task_ids = session_data.get('task_ids', [])
    index = session_data.get('index', 0)

    if index >= len(task_ids):
        return render(
            request,
            'core/sentence_builder_result.html',
            {
                'level': level,
                'level_label': get_level_label(level),
                'session': session_data,
                'progress': level_progress(request.user, level),
            },
        )

    task = get_object_or_404(
        SentenceGameTask,
        pk=task_ids[index],
        level=level,
        is_published=True,
    )
    return render(
        request,
        'core/sentence_builder_play.html',
        {
            'level': level,
            'level_label': get_level_label(level),
            'task': task,
            'shuffled_words': shuffled_words(task),
            'progress': progress,
            'session': session_data,
            'current_num': index + 1,
            'session_total': len(task_ids),
        },
    )


@login_required
@require_POST
def sentence_builder_check(request, level):
    if not is_valid_level(level):
        return JsonResponse({'error': 'Уровень не найден'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Неверный запрос'}, status=400)

    task_id = payload.get('task_id')
    user_order = payload.get('order')
    if task_id is None or not isinstance(user_order, list):
        return JsonResponse({'error': 'Не указаны параметры'}, status=400)

    task = get_object_or_404(SentenceGameTask, pk=task_id, level=level, is_published=True)
    sk = _session_key(level)
    session_data = request.session.get(sk, {})
    task_ids = session_data.get('task_ids', [])
    index = session_data.get('index', 0)

    if index >= len(task_ids) or task_ids[index] != task.id:
        return JsonResponse({'error': 'Сессия устарела. Обновите страницу.'}, status=400)

    session_data['attempts'] = session_data.get('attempts', 0) + 1
    correct = words_match(user_order, task.correct_order)

    if not correct:
        request.session[sk] = session_data
        request.session.modified = True
        return JsonResponse({
            'correct': False,
            'message': 'Неверный порядок. Попробуйте ещё раз.',
        })

    mark_task_solved(request.user, task)
    session_data['correct_count'] = session_data.get('correct_count', 0) + 1
    session_data['index'] = index + 1
    request.session[sk] = session_data
    request.session.modified = True

    progress = level_progress(request.user, level)
    next_index = session_data['index']

    if next_index >= len(task_ids):
        request.session[_result_key(level)] = session_data
        if sk in request.session:
            del request.session[sk]
        request.session.modified = True
        play_url = reverse('core:sentence_builder_play', kwargs={'level': level})
        return JsonResponse({
            'correct': True,
            'done': True,
            'redirect_url': f'{play_url}?finished=1',
            'progress': progress,
            'session': session_data,
        })

    next_task = SentenceGameTask.objects.get(pk=task_ids[next_index])
    return JsonResponse({
        'correct': True,
        'done': False,
        'task': {
            'id': next_task.id,
            'sentence_hint': next_task.sentence_text,
            'words': shuffled_words(next_task),
        },
        'current_num': next_index + 1,
        'session_total': len(task_ids),
        'session_correct': session_data['correct_count'],
        'progress': progress,
    })
