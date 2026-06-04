from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_seed_sentence_tasks'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMatchProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_learned', models.BooleanField(default=False, verbose_name='Изучено')),
                ('learned_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата изучения')),
                ('flashcard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_progress_records', to='core.flashcard', verbose_name='Слово')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_progress', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Прогресс «Сопоставь слова»',
                'verbose_name_plural': 'Прогресс «Сопоставь слова»',
                'ordering': ['-learned_at'],
                'unique_together': {('user', 'flashcard')},
            },
        ),
        migrations.CreateModel(
            name='UserMatchGameStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')], max_length=2, verbose_name='Уровень')),
                ('games_completed', models.PositiveIntegerField(default=0, verbose_name='Игр завершено')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_game_stats', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Статистика игр «Сопоставь слова»',
                'verbose_name_plural': 'Статистика игр «Сопоставь слова»',
                'ordering': ['level'],
                'unique_together': {('user', 'level')},
            },
        ),
    ]
