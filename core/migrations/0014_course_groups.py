from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_seed_match_words'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('slug', models.SlugField(max_length=80, unique=True, verbose_name='URL-идентификатор (slug)')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('courses', models.ManyToManyField(blank=True, related_name='course_groups', to='core.course', verbose_name='Курсы')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_course_groups', to=settings.AUTH_USER_MODEL, verbose_name='Создал')),
                ('tariff_plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='course_groups', to='core.tariffplan', verbose_name='Тариф')),
            ],
            options={
                'verbose_name': 'Группа курсов',
                'verbose_name_plural': 'Группы курсов',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='usersubscription',
            name='course_group',
            field=models.ForeignKey(
                blank=True,
                help_text='Выбранная при оформлении подписки; сохраняется для истории, если группу удалят.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subscriptions',
                to='core.coursegroup',
                verbose_name='Группа курсов',
            ),
        ),
    ]
