from django.db import migrations, connection

def is_postgres():
    return connection.vendor == "postgresql"

def create_extension(apps, schema_editor):
    if is_postgres():
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

def drop_extension(apps, schema_editor):
    if is_postgres():
        schema_editor.execute("DROP EXTENSION IF EXISTS vector;")

class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.RunPython(create_extension, drop_extension),
    ]