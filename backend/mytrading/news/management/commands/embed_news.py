# apps/news/management/commands/embed_news.py
import os, math, json
from typing import List
from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from django.db import transaction
from news.models import NewsItem, NewsChunk

# --- Embedding backend（預設 bge-m3）
_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

_model = None
_dim = 1024  # bge-m3 係 1024；如你換模型，記得同通用向量表 dim 對齊

def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_EMBED_MODEL, device=_DEVICE)
    return _model

def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _load_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=True)
    return [v.astype("float32").tolist() for v in vecs]

def get_embeddings_model():
    # settings.EMBEDDINGS_MODEL = "research.ResearchEmbedding"
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

class Command(BaseCommand):
    help = "Embed NewsChunk into the common embeddings table (object_type='news_chunk')."

    def add_arguments(self, parser):
        parser.add_argument("--days-back", type=int, default=7, help="Only embed recent N days")
        parser.add_argument("--limit", type=int, default=300, help="Max chunks to embed this run")
        parser.add_argument("--news-id", type=int, action="append", help="Only embed specific news id(s)")
        parser.add_argument("--overwrite", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        Emb = get_embeddings_model()
        qb = NewsChunk.objects.select_related("news")
        days_back = opts["days_back"]
        limit = opts["limit"]
        overwrite = opts["overwrite"]

        processed = 0

        if opts["news_id"]:
            qb = qb.filter(news_id__in=opts["news_id"])
        else:
            from django.utils import timezone
            since = timezone.now() - timezone.timedelta(days=days_back)
            qb = qb.filter(news__published_at__gte=since)

        # 避免重複嵌入：過濾掉已有向量的 chunk
        existing = Emb.objects.filter(object_type="news_chunk").values_list("object_id","chunk_id")
        existing_set = set(existing)
        chunks = []
        for ch in qb.order_by("-news__published_at","idx")[:limit]:
            key = (ch.news_id, ch.idx)
            if key in existing_set:
                continue
            chunks.append(ch)

        if not chunks:
            self.stdout.write(self.style.NOTICE("No chunks to embed."))
            return

        texts = [c.text for c in chunks]
        vecs = embed_texts(texts)

        rows = []
        for c, v in zip(chunks, vecs):
            rows.append(Emb(
                object_type="news_chunk",
                object_id=c.news_id,
                chunk_id=c.idx,
                model_name=_EMBED_MODEL,
                dim=_dim,
                vector=v,
                meta={
                    "news_id": c.news_id,
                    "chunk_idx": c.idx,
                    "lang": c.news.lang,
                    "title": c.news.title[:140],
                    "published_at": c.news.published_at.isoformat(),
                    "source": c.news.source,
                },
            ))
        Emb.objects.bulk_create(rows, batch_size=200, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Embedded {len(rows)} chunks with model={_EMBED_MODEL}."))


        # === 你原本的處理流程 ===
        # 例：for chunk in qs: ... create/update embedding ... processed += 1

        # 最後打印統計（機器可解析）
        stats = {"processed": int(processed)}
        self.stdout.write(self.style.SUCCESS(f"[OK] embed_news processed={processed}"))
        self.stdout.write(f"STATS {json.dumps(stats)}")