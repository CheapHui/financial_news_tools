# apps/news/views.py
import os, json
from collections import defaultdict
from typing import List, Dict, Tuple
from django.http import JsonResponse, Http404
from django.db import connection
from django.apps import apps as django_apps
from django.views.decorators.http import require_GET

from news.models import NewsItem, NewsChunk

RESEARCH_TYPES = (
    "company_profile","company_risk","company_catalyst","company_thesis",
    "industry_profile","industry_player"
)

def get_embeddings_model():
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def fetch_news_vectors(news_id: int) -> Dict[int, List[float]]:
    """
    從通用 embeddings 表取該 news 的所有 chunk 向量。
    回傳: {chunk_id -> vector(list[float])}
    """
    Emb = get_embeddings_model()
    rows = Emb.objects.filter(
        object_type="news_chunk", object_id=news_id
    ).values_list("chunk_id", "vector")
    return {cid: vec for (cid, vec) in rows}

def topk_from_research(qv: List[float], k: int):
    """
    用 pgvector cosine 檢索研究 embeddings（命中 HNSW cos 索引）。
    回傳: [(object_type, object_id, chunk_id, sim, meta_json)]
    """
    # 將 Python list 轉換為 PostgreSQL vector 格式
    vector_str = '[' + ','.join(map(str, qv)) + ']'
    
    sql = """
    SELECT object_type, object_id, chunk_id,
           1 - (vector <=> %s::vector) AS sim,
           meta
    FROM research_researchembedding
    WHERE object_type = ANY(%s)
    ORDER BY vector <=> %s::vector
    LIMIT %s;
    """
    with connection.cursor() as cur:
        cur.execute(sql, [vector_str, list(RESEARCH_TYPES), vector_str, k])
        rows = cur.fetchall()
    # rows: obj_type, obj_id, chunk_id, sim, meta(dict)
    return rows

@require_GET
def news_matches(request, news_id: int):
    """
    GET /api/news/<news_id>/matches?topk=10
    合併該新聞所有 chunks 的近鄰結果（research_*），按最高相似度排序取 Top-K。
    """
    try:
        news = NewsItem.objects.get(id=news_id)
    except NewsItem.DoesNotExist:
        raise Http404("news not found")

    try:
        topk = int(request.GET.get("topk", "10"))
        topk = max(1, min(topk, 50))
    except Exception:
        topk = 10

    # 取該新聞 chunks 的已計向量
    vecs = fetch_news_vectors(news.id)
    if not vecs:
        return JsonResponse({
            "news_id": news.id,
            "title": news.title,
            "matches": [],
            "message": "no vectors found for this news (run embed_news first)"
        }, status=200)

    # 對每個 chunk 跑近鄰，彙總到 (object_type, object_id)
    agg = {}  # key -> dict
    per_chunk_hits = defaultdict(list)

    for cid, qv in sorted(vecs.items()):
        rows = topk_from_research(qv, k=topk)
        for obj_type, obj_id, r_chunk_id, sim, meta in rows:
            key = (obj_type, obj_id)
            entry = agg.get(key)
            # 确保 meta 是字典格式
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            meta = meta or {}
            preview = meta.get("chunk_text", "")
            ticker = meta.get("ticker", "")
            industry = meta.get("industry", "")
            best = {
                "chunk_id": r_chunk_id,
                "sim": float(sim),
                "preview": preview,
                "ticker": ticker,
                "industry": industry,
            }
            if not entry or sim > entry["best_sim"]:
                agg[key] = {
                    "object_type": obj_type,
                    "object_id": obj_id,
                    "best_sim": float(sim),
                    "best": best,
                }
            # 收集 per-chunk 命中（給前端需要時用）
            per_chunk_hits[cid].append({
                "object_type": obj_type,
                "object_id": obj_id,
                "sim": float(sim),
            })

    # 取整體 topk
    ranked = sorted(agg.values(), key=lambda x: x["best_sim"], reverse=True)[:topk]
    resp = {
        "news_id": news.id,
        "title": news.title,
        "topk": topk,
        "matches": [
            {
                "object_type": r["object_type"],
                "object_id": r["object_id"],
                "score": r["best_sim"],
                "preview": r["best"]["preview"],
                "ticker": r["best"]["ticker"],
                "industry": r["best"]["industry"],
                "ref_chunk_id": r["best"]["chunk_id"],
            } for r in ranked
        ],
        # 如前端之後想顯示每個 chunk 命中，可打開這一段
        # "by_chunk": per_chunk_hits,
    }
    return JsonResponse(resp, status=200, json_dumps_params={"ensure_ascii": False})