import random

from django.db.models import Count, Sum
from django.utils import timezone

from .flashcards_utils import get_user_group
from .models import Flashcard, FlashcardGroup, UserMatchGameStat, UserMatchProgress

MATCH_ROUND_MIN = 4
MATCH_ROUND_MAX = 6


def match_group_progress(user, group):
    total = group.cards.count()
    if not total:
        return {'total': 0, 'learned': 0, 'active': 0, 'percent': 0}
    learned = UserMatchProgress.objects.filter(
        user=user,
        flashcard__group=group,
        is_learned=True,
    ).count()
    return {
        'total': total,
        'learned': learned,
        'active': total - learned,
        'percent': int((learned / total) * 100),
    }


def default_groups_with_match_progress(user):
    groups = FlashcardGroup.objects.filter(owner__isnull=True).annotate(
        card_count=Count('cards'),
    )
    return [
        {
            'group': g,
            'progress': match_group_progress(user, g),
            'games_completed': UserMatchGameStat.objects.filter(
                user=user,
                level=g.level,
            ).values_list('games_completed', flat=True).first()
            or 0,
        }
        for g in groups
    ]


def pick_round_card_ids(user, group):
    """4–6 слов за раунд: в приоритете ещё не изученные в этой игре."""
    all_ids = list(
        Flashcard.objects.filter(group=group).order_by('order', 'id').values_list('id', flat=True)
    )
    if not all_ids:
        return []

    learned_ids = set(
        UserMatchProgress.objects.filter(
            user=user,
            flashcard__group=group,
            is_learned=True,
        ).values_list('flashcard_id', flat=True)
    )
    unlearned = [pk for pk in all_ids if pk not in learned_ids]
    learned = [pk for pk in all_ids if pk in learned_ids]

    pool = unlearned if len(unlearned) >= MATCH_ROUND_MIN else all_ids
    count = min(MATCH_ROUND_MAX, max(MATCH_ROUND_MIN, len(pool)))
    count = min(count, len(pool))

    if len(pool) <= count:
        chosen = list(pool)
    else:
        chosen = random.sample(pool, count)

    random.shuffle(chosen)
    return chosen


def build_round_columns(card_ids):
    cards = list(
        Flashcard.objects.filter(pk__in=card_ids).order_by('order', 'id')
    )
    en_cards = [{'id': c.id, 'word_en': c.word_en} for c in cards]
    ru_cards = [{'id': c.id, 'word_ru': c.word_ru} for c in cards]
    random.shuffle(ru_cards)
    return en_cards, ru_cards


def mark_match_learned(user, flashcard):
    progress, _ = UserMatchProgress.objects.get_or_create(
        user=user,
        flashcard=flashcard,
    )
    if not progress.is_learned:
        progress.is_learned = True
        progress.learned_at = timezone.now()
        progress.save(update_fields=['is_learned', 'learned_at'])
    return progress


def record_match_game_completed(user, level):
    stat, _ = UserMatchGameStat.objects.get_or_create(user=user, level=level)
    stat.games_completed += 1
    stat.save(update_fields=['games_completed'])
    return stat


def user_match_stats(user):
    learned = UserMatchProgress.objects.filter(user=user, is_learned=True).count()
    games = UserMatchGameStat.objects.filter(user=user).aggregate(
        total=Sum('games_completed'),
    )['total'] or 0
    return {
        'words_learned': learned,
        'games_completed': games,
    }
