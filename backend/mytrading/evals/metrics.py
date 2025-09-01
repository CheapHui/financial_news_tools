import numpy as np

def recall_at_k(ranked_ids, relevant_ids, k: int) -> float:
    """
    ranked_ids: list[str] 已按相似度由高到低排列
    relevant_ids: Iterable[str] ground-truth relevant doc ids
    """
    rel = set(relevant_ids)
    if not rel:
        return 0.0  # 無標註 relevant -> 設為 0（亦可選擇跳過該 query）
    topk = set(ranked_ids[:k])
    return len(rel & topk) / len(rel)

def dcg_at_k(relevance_list, k: int) -> float:
    """
    relevance_list: list[float]，與 ranked_ids 同序的 relevance 分數（0/1 或 graded）
    """
    rel = np.asarray(relevance_list[:k], dtype=float)
    # DCG: sum((2^rel - 1) / log2(i+1))
    discounts = np.log2(np.arange(2, rel.size + 2))
    return np.sum((np.power(2.0, rel) - 1.0) / discounts)

def ndcg_at_k(ranked_ids, relevance_map, k: int) -> float:
    """
    ranked_ids: list[str] 已排序文件ID
    relevance_map: dict[str, float]，doc_id -> relevance grade（無則視為 0）
    """
    gains = [float(relevance_map.get(doc_id, 0.0)) for doc_id in ranked_ids]
    dcg = dcg_at_k(gains, k)
    # IDCG: 將 gains 由高至低排序（理想排序）
    ideal_gains = sorted(gains, reverse=True)
    idcg = dcg_at_k(ideal_gains, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg