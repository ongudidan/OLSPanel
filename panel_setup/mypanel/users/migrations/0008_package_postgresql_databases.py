from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_dbclusternode_channel_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='postgresql_databases',
            field=models.IntegerField(default=0),
        ),
    ]
