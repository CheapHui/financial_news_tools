# research/migrations/000X_enable_pgvector.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("research", "0005_add_vector_index"),
    ]
    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="-- no-op",
        ),
    ]