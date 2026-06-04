from django.db import migrations

LEVEL_WORDS = {
    'A2': [
        ('family', 'семья'),
        ('work', 'работа'),
        ('city', 'город'),
        ('food', 'еда'),
        ('travel', 'путешествие'),
        ('money', 'деньги'),
    ],
    'B1': [
        ('decision', 'решение'),
        ('experience', 'опыт'),
        ('environment', 'окружающая среда'),
        ('relationship', 'отношения'),
        ('opportunity', 'возможность'),
        ('challenge', 'вызов'),
    ],
    'B2': [
        ('achievement', 'достижение'),
        ('consequence', 'последствие'),
        ('perspective', 'перспектива'),
        ('negotiation', 'переговоры'),
        ('assumption', 'предположение'),
        ('controversy', 'спор'),
    ],
    'C1': [
        ('ambiguous', 'двусмысленный'),
        ('comprehensive', 'всеобъемлющий'),
        ('inevitable', 'неизбежный'),
        ('sophisticated', 'сложный, изощрённый'),
        ('reluctant', 'неохотный'),
        ('substantial', 'существенный'),
    ],
    'C2': [
        ('ephemeral', 'мимолётный'),
        ('ubiquitous', 'повсеместный'),
        ('meticulous', 'скрупулёзный'),
        ('quintessential', 'типичный'),
        ('serendipity', 'счастливая случайность'),
        ('paradigm', 'парадигма'),
    ],
}


def seed_words(apps, schema_editor):
    FlashcardGroup = apps.get_model('core', 'FlashcardGroup')
    Flashcard = apps.get_model('core', 'Flashcard')
    for level, words in LEVEL_WORDS.items():
        group = FlashcardGroup.objects.filter(slug=level.lower(), owner__isnull=True).first()
        if not group:
            continue
        if Flashcard.objects.filter(group=group).count() >= 4:
            continue
        for j, (en, ru) in enumerate(words):
            Flashcard.objects.get_or_create(
                group=group,
                word_en=en,
                defaults={'word_ru': ru, 'order': j + 1},
            )


def unseed(apps, schema_editor):
    Flashcard = apps.get_model('core', 'Flashcard')
    FlashcardGroup = apps.get_model('core', 'FlashcardGroup')
    for level in LEVEL_WORDS:
        group = FlashcardGroup.objects.filter(slug=level.lower(), owner__isnull=True).first()
        if not group:
            continue
        for en, _ in LEVEL_WORDS[level]:
            Flashcard.objects.filter(group=group, word_en=en).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_match_game'),
    ]

    operations = [
        migrations.RunPython(seed_words, unseed),
    ]
