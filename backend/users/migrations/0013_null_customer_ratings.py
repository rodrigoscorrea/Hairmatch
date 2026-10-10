from django.db import migrations


def null_customer_ratings(apps, schema_editor):
    """No customer was ever rated: the 5 they hold is a default, so it becomes "no ratings" (AD-010)."""
    User = apps.get_model('users', 'User')
    # By the customer profile, not by `role`: it was stored both as 'customer' and as 'CUSTOMER'.
    User.objects.filter(customer__isnull=False).update(rating=None)


def restore_customer_ratings(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(customer__isnull=False).update(rating=5)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_alter_user_rating'),
    ]

    operations = [
        migrations.RunPython(null_customer_ratings, restore_customer_ratings),
    ]
