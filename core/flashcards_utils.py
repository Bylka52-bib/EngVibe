from django.db.models import Count
from django.utils import timezone

from .models import Flashcard, FlashcardGroup, UserFlashcardProgress


def get_user_group(group_slug, user):
    """Стандартная группа по slug или личная группа пользователя."""
    default = FlashcardGroup.objects.filter(slug=group_slug, owner__isnull=True).first()
    if default:
        return default
    return FlashcardGroup.objects.filter(slug=group_slug, owner=user).first()


def group_progress(user, group):
    total = group.cards.count()
    if not total:
        return {'total': 0, 'learned': 0, 'active': 0, 'percent': 0}
    learned = UserFlashcardProgress.objects.filter(
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


def default_groups_with_progress(user):
    groups = FlashcardGroup.objects.filter(owner__isnull=True).annotate(
        card_count=Count('cards'),
    )
    return [{'group': g, 'progress': group_progress(user, g)} for g in groups]


def user_groups_with_progress(user):
    groups = FlashcardGroup.objects.filter(owner=user).annotate(
        card_count=Count('cards'),
    )
    return [{'group': g, 'progress': group_progress(user, g)} for g in groups]


def reset_group_progress(user, group):
    """Сбросить весь прогресс пользователя по группе."""
    UserFlashcardProgress.objects.filter(
        user=user,
        flashcard__group=group,
    ).delete()


def all_card_ids(group):
    return list(
        Flashcard.objects.filter(group=group)
        .order_by('order', 'id')
        .values_list('id', flat=True)
    )


def unlearned_card_ids(user, group):
    learned_ids = UserFlashcardProgress.objects.filter(
        user=user,
        flashcard__group=group,
        is_learned=True,
    ).values_list('flashcard_id', flat=True)
    return list(
        Flashcard.objects.filter(group=group)
        .exclude(pk__in=learned_ids)
        .order_by('order', 'id')
        .values_list('id', flat=True)
    )


def mark_flashcard_answer(user, flashcard, known):
    progress, _ = UserFlashcardProgress.objects.get_or_create(
        user=user,
        flashcard=flashcard,
    )
    if known:
        progress.is_learned = True
        progress.learned_at = timezone.now()
    else:
        progress.is_learned = False
        progress.learned_at = None
    progress.save()
    return progress
