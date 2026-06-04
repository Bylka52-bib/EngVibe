from django.db import migrations


def dedupe_user_emails(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    seen = {}
    for user in User.objects.exclude(email='').order_by('id'):
        key = user.email.strip().lower()
        if not key:
            continue
        if key in seen:
            user.email = ''
            user.save(update_fields=['email'])
        else:
            seen[key] = user.pk


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0017_usersubscription_setup_completed'),
    ]

    operations = [
        migrations.RunPython(dedupe_user_emails, migrations.RunPython.noop),
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX core_auth_user_email_unique '
                'ON auth_user (email) WHERE email != \'\''
            ),
            reverse_sql='DROP INDEX IF EXISTS core_auth_user_email_unique',
        ),
    ]
