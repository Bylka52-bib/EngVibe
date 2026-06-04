from django.db import migrations


def set_tariff_limits(apps, schema_editor):
    """Базовый — до 3 курсов; премиум/годовой — все курсы (лимиты в админке: max_courses)."""
    TariffPlan = apps.get_model('core', 'TariffPlan')
    basic = TariffPlan.objects.filter(slug='basic').first()
    if basic:
        basic.max_courses = 3
        basic.access_all = False
        basic.save(update_fields=['max_courses', 'access_all'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_course_groups'),
    ]

    operations = [
        migrations.RunPython(set_tariff_limits, noop),
    ]
