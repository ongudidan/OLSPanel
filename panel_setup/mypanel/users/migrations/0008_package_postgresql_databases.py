from django.db import migrations, models


def add_column_if_not_exists(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'packages'")
        if cursor.fetchone():
            cursor.execute("SHOW COLUMNS FROM packages LIKE 'postgresql_databases'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE packages ADD COLUMN postgresql_databases INT(11) DEFAULT 0")


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_dbclusternode_channel_name_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='package',
                    name='postgresql_databases',
                    field=models.IntegerField(default=0),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_column_if_not_exists, reverse_code=migrations.RunPython.noop),
            ],
        ),
    ]
