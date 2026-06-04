from django.db import migrations, models


def mark_existing_setups(apps, schema_editor):
    UserSubscription = apps.get_model('core', 'UserSubscription')
    UserSubscriptionCourse = apps.get_model('core', 'UserSubscriptionCourse')
    for sub in UserSubscription.objects.all():
        if sub.setup_completed:
            continue
        if UserSubscriptionCourse.objects.filter(subscription=sub).exists():
            sub.setup_completed = True
            sub.save(update_fields=['setup_completed'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_restore_premium_access_all'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersubscription',
            name='setup_completed',
            field=models.BooleanField(
                default=False,
                help_text='Пользователь выбрал группу или набор курсов при оформлении подписки.',
                verbose_name='Выбор курсов завершён',
            ),
        ),
        migrations.RunPython(mark_existing_setups, migrations.RunPython.noop),
    ]
