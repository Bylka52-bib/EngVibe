import random

from django.utils import timezone

from .models import SENTENCE_LEVELS, SentenceGameTask, UserSentenceProgress

LEVEL_SLUGS = {code: code for code, _ in SENTENCE_LEVELS}


def get_level_label(level_code):
    return dict(SENTENCE_LEVELS).get(level_code, level_code)


def is_valid_level(level):
    return level in LEVEL_SLUGS


def level_progress(user, level):
    total = SentenceGameTask.objects.filter(level=level, is_published=True).count()
    if not total:
        return {'total': 0, 'solved': 0, 'percent': 0}
    solved = UserSentenceProgress.objects.filter(
        user=user,
        task__level=level,
        task__is_published=True,
        is_solved=True,
    ).count()
    return {
        'total': total,
        'solved': solved,
        'percent': int((solved / total) * 100),
    }


def all_levels_with_progress(user):
    rows = []
    for code, label in SENTENCE_LEVELS:
        rows.append({
            'code': code,
            'label': label,
            'progress': level_progress(user, code),
        })
    return rows


def user_sentence_stats(user):
    total = SentenceGameTask.objects.filter(is_published=True).count()
    solved = UserSentenceProgress.objects.filter(
        user=user,
        task__is_published=True,
        is_solved=True,
    ).count()
    return {
        'total': total,
        'solved': solved,
        'percent': int((solved / total) * 100) if total else 0,
    }


def unsolved_task_ids(user, level):
    solved_ids = UserSentenceProgress.objects.filter(
        user=user,
        task__level=level,
        is_solved=True,
    ).values_list('task_id', flat=True)
    return list(
        SentenceGameTask.objects.filter(level=level, is_published=True)
        .exclude(pk__in=solved_ids)
        .order_by('order', 'id')
        .values_list('id', flat=True)
    )


def all_task_ids(level):
    return list(
        SentenceGameTask.objects.filter(level=level, is_published=True)
        .order_by('order', 'id')
        .values_list('id', flat=True)
    )


def shuffled_words(task):
    words = list(task.correct_order)
    random.shuffle(words)
    return words


def words_match(user_words, correct_words):
    if len(user_words) != len(correct_words):
        return False
    for u, c in zip(user_words, correct_words):
        if str(u).strip().lower() != str(c).strip().lower():
            return False
    return True


def mark_task_solved(user, task):
    progress, _ = UserSentenceProgress.objects.get_or_create(user=user, task=task)
    progress.is_solved = True
    progress.solved_at = timezone.now()
    progress.save()
    return progress


def reset_level_progress(user, level):
    UserSentenceProgress.objects.filter(
        user=user,
        task__level=level,
    ).delete()
