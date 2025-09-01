import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from evals.services import evaluate_embeddings
# from app.ai.llm_client import embed_texts  # 換成你實際 embeddings
embed_texts = None

def _load_records(p: Path):
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    elif p.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        raise CommandError("Only .json or .jsonl is supported")

class Command(BaseCommand):
    help = "Run embedding retrieval evaluation from JSON/JSONL files."

    def add_arguments(self, parser):
        parser.add_argument("--docs", required=True, help="Path to docs json/jsonl")
        parser.add_argument("--queries", required=True, help="Path to queries json/jsonl")
        parser.add_argument("--ks", nargs="+", type=int, default=[1,3,5,10])

    def handle(self, *args, **opts):
        docs_path = Path(opts["docs"])
        queries_path = Path(opts["queries"])
        ks = opts["ks"]

        if not docs_path.exists() or not queries_path.exists():
            raise CommandError("Input files not found.")

        docs = _load_records(docs_path)
        queries = _load_records(queries_path)

        result = evaluate_embeddings(
            docs=docs, queries=queries, ks=ks, embed_texts=embed_texts
        )
        self.stdout.write(self.style.SUCCESS(json.dumps(result, ensure_ascii=False, indent=2)))