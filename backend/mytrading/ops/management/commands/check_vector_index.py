from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Show pgvector index usage and a sample EXPLAIN."

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'research_researchembedding';
            """)
            idx = cur.fetchall()
            self.stdout.write("Indexes on research_researchembedding:")
            for name,defn in idx:
                self.stdout.write(f"  - {name}: {defn}")

            cur.execute("SET hnsw.ef_search = 120;")
            cur.execute("""
            EXPLAIN
            SELECT id FROM research_researchembedding
            ORDER BY vector <=> (SELECT vector FROM research_researchembedding LIMIT 1)
            LIMIT 10;
            """)
            plan = "\n".join(r[0] for r in cur.fetchall())
            self.stdout.write("\nSample EXPLAIN:\n" + plan)