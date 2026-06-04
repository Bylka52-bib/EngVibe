from django.db import migrations

TASKS = [
    ('beginner', 'The cat is sleeping.', ['The', 'cat', 'is', 'sleeping.'], 1),
    ('beginner', 'I like coffee.', ['I', 'like', 'coffee.'], 2),
    ('beginner', 'She is my friend.', ['She', 'is', 'my', 'friend.'], 3),
    ('beginner', 'We live in Moscow.', ['We', 'live', 'in', 'Moscow.'], 4),
    ('beginner', 'It is a sunny day.', ['It', 'is', 'a', 'sunny', 'day.'], 5),
    ('intermediate', 'Have you ever been to London?', ['Have', 'you', 'ever', 'been', 'to', 'London?'], 1),
    ('intermediate', 'I have never tried sushi before.', ['I', 'have', 'never', 'tried', 'sushi', 'before.'], 2),
    ('intermediate', 'She does not like cold weather.', ['She', 'does', 'not', 'like', 'cold', 'weather.'], 3),
    ('intermediate', 'Where did you buy this book?', ['Where', 'did', 'you', 'buy', 'this', 'book?'], 4),
    ('intermediate', 'They have been waiting for an hour.', ['They', 'have', 'been', 'waiting', 'for', 'an', 'hour.'], 5),
    ('advanced', 'Never have I seen such a beautiful sunset.', ['Never', 'have', 'I', 'seen', 'such', 'a', 'beautiful', 'sunset.'], 1),
    ('advanced', 'Not only did he apologize, but he also offered to help.', ['Not', 'only', 'did', 'he', 'apologize,', 'but', 'he', 'also', 'offered', 'to', 'help.'], 2),
    ('advanced', 'Were it not for your support, I would have failed.', ['Were', 'it', 'not', 'for', 'your', 'support,', 'I', 'would', 'have', 'failed.'], 3),
    ('advanced', 'Rarely do we get a chance like this.', ['Rarely', 'do', 'we', 'get', 'a', 'chance', 'like', 'this.'], 4),
    ('advanced', 'Little did she know what was about to happen.', ['Little', 'did', 'she', 'know', 'what', 'was', 'about', 'to', 'happen.'], 5),
]


def seed_tasks(apps, schema_editor):
    SentenceGameTask = apps.get_model('core', 'SentenceGameTask')
    for level, text, order_words, order in TASKS:
        SentenceGameTask.objects.get_or_create(
            level=level,
            sentence_text=text,
            defaults={
                'correct_order': order_words,
                'order': order,
                'is_published': True,
            },
        )


def unseed(apps, schema_editor):
    SentenceGameTask = apps.get_model('core', 'SentenceGameTask')
    texts = [t[1] for t in TASKS]
    SentenceGameTask.objects.filter(sentence_text__in=texts).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_sentence_builder'),
    ]

    operations = [
        migrations.RunPython(seed_tasks, unseed),
    ]
