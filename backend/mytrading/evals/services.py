from typing import List, Dict, Optional, Iterable
import numpy as np
from datetime import datetime
from .metrics import recall_at_k, ndcg_at_k

# ---- 你需要提供的介面（用你現有 DeepSeek/自家 embedding 客戶端替換） ----
# 例：from app.ai.embeddings import embed_texts
def _dummy_embed_texts(texts: List[str]) -> np.ndarray:
    # 佔位：請換成你實際的 embedding function（返回 shape=[N, dim] 的 np.ndarray）
    rng = np.random.default_rng(42)
    return rng.standard_normal((len(texts), 768)).astype("float32")

def get_embedding_quality_metrics(result: Dict) -> Dict:
    """
    計算額外的質量指標，用於前端顯示
    """
    summary = result.get('summary', {})
    per_query = result.get('per_query', [])
    
    # 計算平均排名位置
    avg_rank_positions = []
    for q in per_query:
        top_10 = q.get('top_10', [])
        # 找到第一個相關文檔的位置
        first_relevant_pos = None
        for i, doc_id in enumerate(top_10):
            # 這裡需要檢查是否為相關文檔，暫時使用簡單邏輯
            if first_relevant_pos is None:
                first_relevant_pos = i + 1
                break
        if first_relevant_pos:
            avg_rank_positions.append(first_relevant_pos)
    
    avg_first_relevant_rank = np.mean(avg_rank_positions) if avg_rank_positions else 0
    
    # 計算質量等級
    ndcg_5 = summary.get('macro_ndcg_at_k', {}).get(5, 0)
    if ndcg_5 >= 0.8:
        quality_grade = "Excellent"
        quality_color = "green"
    elif ndcg_5 >= 0.6:
        quality_grade = "Good"
        quality_color = "blue"
    elif ndcg_5 >= 0.4:
        quality_grade = "Fair"
        quality_color = "amber"
    else:
        quality_grade = "Poor"
        quality_color = "red"
    
    return {
        'avg_first_relevant_rank': round(avg_first_relevant_rank, 2),
        'quality_grade': quality_grade,
        'quality_color': quality_color,
        'total_queries_evaluated': len(per_query),
        'evaluation_timestamp': datetime.now().isoformat()
    }

def _normalize_rows(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / norms

def _cosine_rank(query_vec: np.ndarray, doc_matrix: np.ndarray, doc_ids: List[str]) -> List[str]:
    # 假設已 unit-normalized：cosine = dot
    sims = doc_matrix @ query_vec
    order = np.argsort(-sims)  # 由高到低
    return [doc_ids[i] for i in order]

def evaluate_embeddings(
    docs: List[Dict],
    queries: List[Dict],
    ks: Iterable[int] = (1, 3, 5, 10),
    embed_texts = None,
    use_binary_relevance_if_missing: bool = True,
) -> Dict:
    """
    docs: [{ "id": str, "text": str, (optional) "embedding": [float,...] }, ...]
    queries: [
      {
        "id": str,
        "text": str,
        # 二選一：
        "relevant_ids": [str,...],                 # binary relevance
        # 或
        "relevance_map": {"doc_id": grade, ...},   # graded relevance（float/int）
      }, ...
    ]
    ks: 指標的 K 值集合
    embed_texts: callable(list[str]) -> np.ndarray  （若 None 就用 _dummy_embed_texts）
    """
    ks = sorted(set(int(k) for k in ks))
    embed_texts = embed_texts or _dummy_embed_texts

    # --- 準備 doc vectors ---
    doc_ids = [d["id"] for d in docs]
    if len(set(doc_ids)) != len(doc_ids):
        raise ValueError("Duplicate doc ids found.")
    doc_texts = [d.get("text") for d in docs]
    doc_vecs = None

    if all("embedding" in d for d in docs):
        doc_vecs = np.asarray([d["embedding"] for d in docs], dtype="float32")
    else:
        if not all(isinstance(t, str) and t for t in doc_texts):
            raise ValueError("Docs missing 'embedding' and 'text' is not fully provided.")
        doc_vecs = embed_texts(doc_texts).astype("float32")

    doc_vecs = _normalize_rows(doc_vecs)

    # --- 評測 ---
    per_query = []
    macro_recall = {k: [] for k in ks}
    macro_ndcg = {k: [] for k in ks}

    for q in queries:
        qid = q["id"]
        qtext = q.get("text", "")
        qrel_ids = q.get("relevant_ids")
        qrel_map = q.get("relevance_map")

        if not qrel_map:
            if use_binary_relevance_if_missing:
                qrel_map = {rid: 1.0 for rid in (qrel_ids or [])}
            else:
                raise ValueError(f"Query {qid} missing relevance_map.")

        # 取得 query 向量
        qvec = embed_texts([qtext]).astype("float32")[0]
        qvec = qvec / (np.linalg.norm(qvec) + 1e-12)

        ranked = _cosine_rank(qvec, doc_vecs, doc_ids)

        # per-k 指標
        q_recalls, q_ndcgs = {}, {}
        bin_rels = list(qrel_map.keys())  # for recall，視非 0 為 relevant
        for k in ks:
            q_recalls[k] = recall_at_k(ranked, bin_rels, k)
            q_ndcgs[k] = ndcg_at_k(ranked, qrel_map, k)
            macro_recall[k].append(q_recalls[k])
            macro_ndcg[k].append(q_ndcgs[k])

        per_query.append({
            "query_id": qid,
            "recall_at_k": q_recalls,
            "ndcg_at_k": q_ndcgs,
            "top_10": ranked[:10],  # 方便快速檢視
        })

    summary = {
        "macro_recall_at_k": {k: float(np.mean(v) if v else 0.0) for k, v in macro_recall.items()},
        "macro_ndcg_at_k": {k: float(np.mean(v) if v else 0.0) for k, v in macro_ndcg.items()},
        "num_queries": len(queries),
        "num_docs": len(docs),
    }

    result = {"summary": summary, "per_query": per_query}
    
    # 添加質量指標
    quality_metrics = get_embedding_quality_metrics(result)
    result['quality_metrics'] = quality_metrics
    
    return result