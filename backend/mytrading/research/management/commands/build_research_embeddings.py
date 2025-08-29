# research/management/commands/build_research_embeddings.py
import os, math, json
from typing import List, Tuple
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps as django_apps
from django.utils import timezone

from reference.models import Company, Industry
from research.models import (
    CompanyProfile, CompanyRisk, CompanyCatalyst, CompanyThesis,
    IndustryProfile, IndustryPlayer,
)

# ---- 環境/設定 ----
_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")   # 1024 維
_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
_BATCH = int(os.getenv("EMBEDDING_BATCH", "64"))             # 32/64/256 視機器
_CHUNK_MAX = int(os.getenv("EMBEDDING_CHARS", "1200"))       # 每塊字元
_OVERLAP = int(os.getenv("EMBEDDING_OVERLAP", "150"))        # 重疊

_model = None
_DIM = 1024  # bge-m3 = 1024；如改模型記得同步改通用表 dim

def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_EMBED_MODEL, device=_DEVICE)
    return _model

def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _load_model()
    vecs = model.encode(
        texts,
        batch_size=_BATCH,
        normalize_embeddings=True,  # cosine 相似度更穩
        show_progress_bar=True,
    )
    return [v.astype("float32").tolist() for v in vecs]

def get_embeddings_model():
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def chunk_text(text: str, max_chars=_CHUNK_MAX, overlap=_OVERLAP):
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        end = min(len(text), i + max_chars)
        chunk = text[i:end]
        chunks.append(chunk)
        if end == len(text):
            break
        i = max(0, end - overlap)
    return chunks

# ---- 要處理的 object_types 映射：Model -> (object_type, queryset_fn, meta_builder) ----
def _meta_common(obj, extra=None):
    m = {"updated_at": timezone.now().isoformat()}
    if extra: m.update(extra)
    return m

MAPPINGS = [
    # 公司層
    (CompanyProfile,     "company_profile",
     lambda: CompanyProfile.objects.select_related("company").all(),
     lambda o, k: _meta_common(o, {"company_id": o.company_id, "ticker": o.company.ticker})),
    (CompanyRisk,        "company_risk",
     lambda: CompanyRisk.objects.select_related("company").all(),
     lambda o, k: _meta_common(o, {"company_id": o.company_id, "ticker": o.company.ticker,
                                   "risk_category": o.category, "horizon": o.horizon})),
    (CompanyCatalyst,    "company_catalyst",
     lambda: CompanyCatalyst.objects.select_related("company").all(),
     lambda o, k: _meta_common(o, {"company_id": o.company_id, "ticker": o.company.ticker,
                                   "positive": o.positive})),
    (CompanyThesis,      "company_thesis",
     lambda: CompanyThesis.objects.select_related("company").all(),
     lambda o, k: _meta_common(o, {"company_id": o.company_id, "ticker": o.company.ticker,
                                   "side": o.side})),
    # 行業層
    (IndustryProfile,    "industry_profile",
     lambda: IndustryProfile.objects.select_related("industry").all(),
     lambda o, k: _meta_common(o, {"industry_id": o.industry_id, "industry": o.industry.name})),
    (IndustryPlayer,     "industry_player",
     lambda: IndustryPlayer.objects.select_related("industry","company").all(),
     lambda o, k: _meta_common(o, {"industry_id": o.industry_id, "industry": o.industry.name,
                                   "ticker": (o.company.ticker if o.company_id else o.symbol), "role": o.role})),
]

# 讀取文本（優先 context_text）
def to_text(obj) -> str:
    # 各 model 已有 to_card_text()，會優先用 context_text
    if hasattr(obj, "to_card_text"):
        return (obj.to_card_text() or "").strip()
    # 後備（理論上用唔着）
    return (getattr(obj, "context_text", "") or "").strip()

class Command(BaseCommand):
    help = "Build embeddings for research objects and upsert into the common embeddings table."

    def add_arguments(self, parser):
        parser.add_argument("--types", type=str, default="company_profile,company_risk,company_catalyst,company_thesis,industry_profile,industry_player",
                            help="Comma-separated object_types to process")
        parser.add_argument("--limit", type=int, default=0, help="Per-type object limit (0 = no limit)")
        parser.add_argument("--overwrite", action="store_true", help="Delete existing embeddings for selected types before insert")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, just report counts")

    @transaction.atomic
    def handle(self, *args, **opts):
        Emb = get_embeddings_model()
        want_types = {t.strip() for t in (opts["types"] or "").split(",") if t.strip()}
        limit = int(opts["limit"])
        overwrite = opts["overwrite"]
        dry = opts["dry_run"]

        # optional 清理
        if overwrite:
            deleted = Emb.objects.filter(object_type__in=want_types).delete()[0]
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing embeddings for {sorted(want_types)}"))

        total_chunks = 0
        total_objs = 0
        rows_to_insert = []

        for Model, obj_type, qs_fn, meta_fn in MAPPINGS:
            if obj_type not in want_types:
                continue
            qs = qs_fn().order_by("pk")
            if limit > 0:
                qs = qs[:limit]
            cnt = qs.count()
            if cnt == 0:
                continue
            self.stdout.write(self.style.NOTICE(f"[{obj_type}] scanning {cnt} objects..."))

            # 濾已嵌入的（避免重複）
            existing = set(Emb.objects.filter(object_type=obj_type).values_list("object_id","chunk_id"))
            processed_objs = 0

            for obj in qs:
                text = to_text(obj)
                if not text:
                    continue
                chunks = chunk_text(text)
                for idx, chunk in enumerate(chunks):
                    key = (obj.pk, idx)
                    if key in existing:
                        continue
                    rows_to_insert.append(Emb(
                        object_type=obj_type,
                        object_id=obj.pk,
                        chunk_id=idx,
                        model_name=_EMBED_MODEL,
                        dim=_DIM,
                        vector=[],  # 先放空，稍後批量填
                        meta=meta_fn(obj, idx) | {"chunk_idx": idx},
                    ))
                processed_objs += 1
                total_chunks += len(chunks)
            total_objs += processed_objs

        if not rows_to_insert:
            self.stdout.write(self.style.WARNING("No new chunks to embed."))
            return

        # 先把 text 提取出來做 embedding
        texts = []
        for r in rows_to_insert:
            # 反查原文：用 object_type 對應 Model 再 to_card_text + chunk_text 同 idx 取內容
            # 為減少重算，這裡簡化：直接在上面計算時順便把 chunk 文本塞入 meta
            pass  # 我們改為在上面塞文本

        # --- 改：在上面 rows_to_insert.meta 加入 'chunk_text'，此處直接讀出
        # 重新生成 rows，這次把 chunk_text 寫入 meta
        rows_final = []
        texts = []
        idx = 0
        # 由於上面暫未把 chunk 文本保存在 meta，我哋重走一次輕量流程（不掃 DB）：
        temp_map = {}
        for Model, obj_type, qs_fn, meta_fn in MAPPINGS:
            if obj_type not in want_types:
                continue
            for obj in qs_fn():
                text = to_text(obj)
                if not text:
                    continue
                for cidx, chunk in enumerate(chunk_text(text)):
                    temp_map[(obj_type, obj.pk, cidx)] = chunk

        # 為 rows_to_insert 補 chunk 文本
        for r in rows_to_insert:
            chunk = temp_map.get((r.object_type, r.object_id, r.chunk_id))
            if not chunk:
                continue
            texts.append(chunk)
            r.meta = (r.meta or {}) | {"chunk_text": chunk[:240]}  # meta 存一小段 preview
            rows_final.append(r)

        # 真正嵌入
        vecs = embed_texts(texts)

        # 寫回向量
        for r, v in zip(rows_final, vecs):
            r.vector = v

        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"[DRY] Objects processed={total_objs}, chunks embedded={len(rows_final)}"
            ))
            return

        # 批量插入
        Emb.objects.bulk_create(rows_final, batch_size=200, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f"[OK] Objects processed={total_objs}, chunks embedded={len(rows_final)}, model={_EMBED_MODEL}"
        ))