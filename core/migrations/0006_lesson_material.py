from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_tariff_subscriptions'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='material',
            field=models.TextField(
                blank=True,
                help_text='Основное содержание урока: текст, списки, ссылки (отображается на странице урока).',
            ),
        ),
    ]
