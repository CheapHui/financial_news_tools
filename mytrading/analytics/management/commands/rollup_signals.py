import math
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from django.apps import apps as django_apps

from news.models import NewsItem, NewsChunk
from analytics.models import AnalyticsIndustrySignal
from reference.models import Company, Industry
from research.models import AnalyticsCompanySignal
from research.models import (
    CompanyProfile, CompanyRisk, CompanyCatalyst, CompanyThesis,
    IndustryProfile, IndustryPlayer
)

# 研究 object types
COMPANY_TYPES  = ("company_profile","company_risk","company_catalyst","company_thesis")
INDUSTRY_TYPES = ("industry_profile","industry_player")
ALL_TYPES = COMPANY_TYPES + INDUSTRY_TYPES

# polarity / half-life（可改 DB/設定）
POLARITY_DEFAULT = {
    "company_profile":   +0.2,
    "company_risk":      -1.0,
    "company_catalyst":  +1.0,
    "company_thesis":    +0.0,  # 依 side 再覆蓋
    "industry_profile":  +0.1,  # 行業命中偏中性，視分配時再調
    "industry_player":   +0.2,  # 命中某 player（偏公司層），同時視分配公司
}

HALF_LIFE = {
    "company_profile":   90,
    "company_risk":      60,
    "company_catalyst":  20,
    "company_thesis":    45,
    "industry_profile":  60,
    "industry_player":   45,
}

def get_embeddings_model():
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def cosine_topk(qv, types, k=5):
    # 確保 qv 是正確的格式並轉換為 PostgreSQL vector 字符串
    if hasattr(qv, 'tolist'):  # NumPy 數組
        qv_list = qv.tolist()
    elif isinstance(qv, (list, tuple)):
        qv_list = list(qv)
    else:
        qv_list = [float(x) for x in qv]
    
    vector_str = '[' + ','.join(map(str, qv_list)) + ']'
    
    sql = """
    SELECT object_type, object_id, chunk_id,
           1 - (vector <=> %s::vector) AS sim
    FROM research_researchembedding
    WHERE object_type = ANY(%s)
    ORDER BY vector <=> %s::vector
    LIMIT %s;
    """
    with connection.cursor() as cur:
        cur.execute(sql, [vector_str, list(types), vector_str, k])
        return cur.fetchall()

def days_diff(a, b): return abs((a - b).days)

def resolve_company_signal(obj_type, obj_id):
    """回傳 (company_id, polarity)；公司向研究物件映射"""
    company_id = None
    polarity = POLARITY_DEFAULT.get(obj_type, 0.0)

    if obj_type == "company_profile":
        try:
            cp = CompanyProfile.objects.only("company_id").get(id=obj_id)
            company_id = cp.company_id
        except CompanyProfile.DoesNotExist:
            pass
    elif obj_type == "company_risk":
        try:
            r = CompanyRisk.objects.only("company_id").get(id=obj_id)
            company_id = r.company_id; polarity = -1.0
        except CompanyRisk.DoesNotExist:
            pass
    elif obj_type == "company_catalyst":
        try:
            c = CompanyCatalyst.objects.only("company_id","positive").get(id=obj_id)
            company_id = c.company_id; polarity = +1.0 if c.positive else -1.0
        except CompanyCatalyst.DoesNotExist:
            pass
    elif obj_type == "company_thesis":
        try:
            t = CompanyThesis.objects.only("company_id","side").get(id=obj_id)
            company_id = t.company_id; polarity = +0.5 if t.side == "for" else -0.5
        except CompanyThesis.DoesNotExist:
            pass
    return company_id, polarity

def resolve_industry_signal(obj_type, obj_id):
    """回傳 (industry_id, polarity)；行業向研究物件映射"""
    industry_id = None
    polarity = POLARITY_DEFAULT.get(obj_type, 0.0)
    if obj_type == "industry_profile":
        try:
            ip = IndustryProfile.objects.only("industry_id").get(id=obj_id)
            industry_id = ip.industry_id
        except IndustryProfile.DoesNotExist:
            pass
    elif obj_type == "industry_player":
        try:
            pl = IndustryPlayer.objects.only("industry_id").get(id=obj_id)
            industry_id = pl.industry_id
        except IndustryPlayer.DoesNotExist:
            pass
    return industry_id, polarity

def industry_distribution_weights(industry_id, top_n=8):
    """
    由 IndustryPlayer 取主要公司及權重：
      - 先過濾有 company_id 的 player
      - 優先使用 market_cap_usd 作權重；缺失則回退平均
      - 只取 top_n（按市值）
    回傳 list[(company_id, weight_0_1)]，權重總和=1 或 0（無法分配）
    """
    players = (IndustryPlayer.objects
               .select_related("company")
               .filter(industry_id=industry_id, company__isnull=False))
    rows = []
    for p in players:
        cap = p.market_cap_usd or 0.0
        rows.append((p.company_id, float(cap)))
    if not rows:
        return []

    # sort by cap desc，取 top_n
    rows = sorted(rows, key=lambda x: x[1], reverse=True)[:max(1, top_n)]
    # 如市值全 0 → 平均
    total_cap = sum(x[1] for x in rows)
    if total_cap <= 0:
        w = 1.0 / len(rows)
        return [(cid, w) for (cid, _) in rows]
    return [(cid, cap/total_cap) for (cid, cap) in rows]

def get_news_vectors(news_id):
    Emb = get_embeddings_model()
    rows = Emb.objects.filter(object_type="news_chunk", object_id=news_id)\
                      .values_list("chunk_id","vector")
    return {cid: vec for (cid, vec) in rows}

class Command(BaseCommand):
    help = "Aggregate recent news→research matches into company-level & industry-level signals (with time decay & polarity)."

    def add_arguments(self, parser):
        parser.add_argument("--days-back", type=int, default=7)
        parser.add_argument("--window-days", type=int, default=7)
        parser.add_argument("--topk-per-chunk", type=int, default=5)
        parser.add_argument("--min-sim", type=float, default=0.35)
        parser.add_argument("--overwrite", action="store_true")

        # 行業分配策略
        parser.add_argument("--industry-to-company", choices=["weight","equal","off"], default="weight",
                            help="把 industry 命中分配到公司：weight=按市值；equal=平均；off=不分配")
        parser.add_argument("--industry-top-n", type=int, default=8, help="只把行業信號分配到市值前N家公司")
        parser.add_argument("--include-industry-signal", action="store_true", help="同時計算行業級信號（AnalyticsIndustrySignal）")

    @transaction.atomic
    def handle(self, *args, **opts):
        now = timezone.now()
        since = now - timezone.timedelta(days=opts["days_back"])
        window_start = now - timezone.timedelta(days=opts["window_days"])
        window_end = now

        topk = opts["topk_per_chunk"]; min_sim = opts["min_sim"]
        overwrite = opts["overwrite"]
        dist_mode = opts["industry_to_company"]
        top_n = max(1, opts["industry_top_n"])
        include_industry = opts["include_industry_signal"]

        # 取最近新聞 chunks
        chunks = (NewsChunk.objects.select_related("news")
                  .filter(news__published_at__gte=since)
                  .order_by("-news__published_at","idx"))

        # 聚合容器
        comp_score = defaultdict(float)
        comp_details = defaultdict(list)
        comp_news_abs = defaultdict(lambda: defaultdict(float))   # company_id -> news_id -> |contrib|max

        ind_score = defaultdict(float)
        ind_details = defaultdict(list)
        ind_news_abs = defaultdict(lambda: defaultdict(float))

        # 主循環
        for ch in chunks:
            vecs = get_news_vectors(ch.news_id)
            if ch.idx not in vecs:
                continue
            qv = vecs[ch.idx]
            dd = days_diff(now, ch.news.published_at)

            # 先查公司類 hits
            for obj_type, obj_id, r_cid, sim in cosine_topk(qv, COMPANY_TYPES, k=topk):
                if sim < min_sim: continue
                company_id, polarity = resolve_company_signal(obj_type, obj_id)
                if not company_id: continue
                hl = HALF_LIFE.get(obj_type, 60)
                decay = 0.5 ** (dd / hl)
                contrib = float(sim) * float(polarity) * float(decay)
                comp_score[company_id] += contrib
                comp_details[company_id].append({
                    "news_id": ch.news_id, "chunk_id": ch.idx,
                    "obj_type": obj_type, "obj_id": obj_id,
                    "sim": float(sim), "polarity": float(polarity),
                    "decay": float(decay), "contrib": float(contrib),
                })
                comp_news_abs[company_id][ch.news_id] = max(comp_news_abs[company_id].get(ch.news_id,0.0), abs(contrib))

            # 再查行業類 hits
            ind_hits = cosine_topk(qv, INDUSTRY_TYPES, k=topk)
            for obj_type, obj_id, r_cid, sim in ind_hits:
                if sim < min_sim: continue
                industry_id, ind_polarity = resolve_industry_signal(obj_type, obj_id)
                if not industry_id: continue
                hl = HALF_LIFE.get(obj_type, 60)
                decay = 0.5 ** (dd / hl)
                ind_contrib = float(sim) * float(ind_polarity) * float(decay)

                # 行業級聚合（如需）
                if include_industry:
                    ind_score[industry_id] += ind_contrib
                    ind_details[industry_id].append({
                        "news_id": ch.news_id, "chunk_id": ch.idx,
                        "obj_type": obj_type, "obj_id": obj_id,
                        "sim": float(sim), "polarity": float(ind_polarity),
                        "decay": float(decay), "contrib": float(ind_contrib),
                    })
                    ind_news_abs[industry_id][ch.news_id] = max(
                        ind_news_abs[industry_id].get(ch.news_id,0.0), abs(ind_contrib)
                    )

                # 分配到公司
                if dist_mode != "off":
                    if obj_type == "industry_player":
                        # 若命中具體 player，且該 player 綁定 company → 100% 給該公司
                        try:
                            pl = IndustryPlayer.objects.only("company_id","industry_id").get(id=obj_id)
                            if pl.company_id:
                                comp_score[pl.company_id] += ind_contrib
                                comp_details[pl.company_id].append({
                                    "news_id": ch.news_id, "chunk_id": ch.idx,
                                    "obj_type": obj_type, "obj_id": obj_id,
                                    "sim": float(sim), "polarity": float(ind_polarity),
                                    "decay": float(decay), "contrib": float(ind_contrib),
                                    "note": "player→company 100%",
                                })
                                comp_news_abs[pl.company_id][ch.news_id] = max(
                                    comp_news_abs[pl.company_id].get(ch.news_id,0.0), abs(ind_contrib)
                                )
                                continue
                        except IndustryPlayer.DoesNotExist:
                            pass

                    # industry_profile 或無法直接對應 player→company：用權重/平均分配
                    if dist_mode == "weight":
                        weights = industry_distribution_weights(industry_id, top_n=top_n)
                    else:
                        # equal
                        weights = industry_distribution_weights(industry_id, top_n=top_n)
                        if weights:
                            w = 1.0 / len(weights)
                            weights = [(cid, w) for (cid, _) in weights]

                    for cid, w in weights:
                        c_contrib = ind_contrib * float(w)
                        comp_score[cid] += c_contrib
                        comp_details[cid].append({
                            "news_id": ch.news_id, "chunk_id": ch.idx,
                            "obj_type": obj_type, "obj_id": obj_id,
                            "sim": float(sim), "polarity": float(ind_polarity),
                            "decay": float(decay), "contrib": float(c_contrib),
                            "note": f"industry→company w={w:.3f}",
                        })
                        comp_news_abs[cid][ch.news_id] = max(
                            comp_news_abs[cid].get(ch.news_id,0.0), abs(c_contrib)
                        )

        # 寫回 DB（公司級）
        if overwrite:
            AnalyticsCompanySignal.objects.filter(window_start__lte=window_start, window_end__gte=window_end).delete()

        n_comp = 0
        for cid, score in comp_score.items():
            news_scores = comp_news_abs[cid]
            top_news_ids = [nid for nid,_ in sorted(news_scores.items(), key=lambda x: x[1], reverse=True)[:10]]
            AnalyticsCompanySignal.objects.update_or_create(
                company_id=cid, window_start=window_start, window_end=window_end,
                defaults=dict(score=score, details_json=comp_details[cid], top_news_ids=top_news_ids)
            )
            n_comp += 1

        # 寫回 DB（行業級）
        n_ind = 0
        if include_industry:
            if overwrite:
                AnalyticsIndustrySignal.objects.filter(window_start__lte=window_start, window_end__gte=window_end).delete()
            for iid, score in ind_score.items():
                news_scores = ind_news_abs[iid]
                top_news_ids = [nid for nid,_ in sorted(news_scores.items(), key=lambda x: x[1], reverse=True)[:10]]
                AnalyticsIndustrySignal.objects.update_or_create(
                    industry_id=iid, window_start=window_start, window_end=window_end,
                    defaults=dict(score=score, details_json=ind_details[iid], top_news_ids=top_news_ids)
                )
                n_ind += 1

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Rolled up signals → companies={n_comp}, industries={n_ind} "
            f"Window={window_start.date()}..{window_end.date()} "
            f"mode={dist_mode}, top_n={top_n}, include_industry={include_industry}"
        ))