# research/migrations/000Y_hnsw_cosine_index.py
from django.db import migrations

INDEX_NAME = "resemb_hnsw_cosine"

class Migration(migrations.Migration):
    dependencies = [
        ("research", "0006_enable_pgvector"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
            CREATE INDEX IF NOT EXISTS {INDEX_NAME}
            ON research_researchembedding
            USING hnsw (vector vector_cosine_ops);
            """,
            reverse_sql=f"DROP INDEX IF EXISTS {INDEX_NAME};",
        ),
    ]