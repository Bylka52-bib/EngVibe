# Generated manually for EngVibe

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_course_teachers_review_user_usertestresult_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsletterSubscriber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='course',
            name='is_premium',
            field=models.BooleanField(default=False),
        ),
    ]
