from django.db import migrations

LEVELS = ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')

SAMPLE_A1 = [
    ('cat', 'кошка'),
    ('dog', 'собака'),
    ('book', 'книга'),
    ('water', 'вода'),
    ('hello', 'привет'),
    ('good', 'хороший'),
    ('day', 'день'),
    ('house', 'дом'),
    ('friend', 'друг'),
    ('time', 'время'),
]


def seed_groups(apps, schema_editor):
    FlashcardGroup = apps.get_model('core', 'FlashcardGroup')
    Flashcard = apps.get_model('core', 'Flashcard')
    for i, level in enumerate(LEVELS):
        group, created = FlashcardGroup.objects.get_or_create(
            slug=level.lower(),
            owner=None,
            defaults={
                'name': f'Слова уровня {level}',
                'level': level,
                'order': i + 1,
            },
        )
        if level == 'A1' and created:
            for j, (en, ru) in enumerate(SAMPLE_A1):
                Flashcard.objects.create(
                    group=group,
                    word_en=en,
                    word_ru=ru,
                    order=j + 1,
                )


def unseed(apps, schema_editor):
    FlashcardGroup = apps.get_model('core', 'FlashcardGroup')
    FlashcardGroup.objects.filter(owner__isnull=True, slug__in=[l.lower() for l in LEVELS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_flashcards'),
    ]

    operations = [
        migrations.RunPython(seed_groups, unseed),
    ]
