from django.db import migrations


def restore_premium(apps, schema_editor):
    TariffPlan = apps.get_model('core', 'TariffPlan')
    premium = TariffPlan.objects.filter(slug='premium').first()
    if premium:
        premium.access_all = True
        premium.max_courses = None
        premium.save(update_fields=['access_all', 'max_courses'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_tariff_max_courses_labels'),
    ]

    operations = [
        migrations.RunPython(restore_premium, noop),
    ]
