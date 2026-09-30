from django.db import migrations
from django.db.models import Count


def mark_duplicated_phones(apps, schema_editor):
    """Before phone becomes unique: the oldest user keeps a repeated phone, the others get `dup-<id>` to be fixed by hand."""
    User = apps.get_model('users', 'User')
    repeated = (
        User.objects.values('phone').annotate(total=Count('id')).filter(total__gt=1).values_list('phone', flat=True)
    )
    for phone in list(repeated):
        for user in User.objects.filter(phone=phone).order_by('id')[1:]:
            user.phone = f'dup-{user.id}'
            user.save(update_fields=['phone'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_cognito_sub'),
    ]

    operations = [
        migrations.RunPython(mark_duplicated_phones, migrations.RunPython.noop),
    ]
