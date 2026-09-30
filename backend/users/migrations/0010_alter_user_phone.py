from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_dedupe_user_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
