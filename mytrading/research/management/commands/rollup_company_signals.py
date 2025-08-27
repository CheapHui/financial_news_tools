# apps/analytics/management/commands/rollup_company_signals.py
import math
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from django.apps import apps as django_apps

from news.models import NewsItem, NewsChunk
from research.models import AnalyticsCompanySignal
from research.models import CompanyProfile, CompanyRisk, CompanyCatalyst, CompanyThesis

RESEARCH_TYPES = (
    "company_profile","company_risk","company_catalyst","company_thesis"
)

# polarity / half-life 默認（如未能查到更細資料時）
POLARITY_DEFAULT = {
    "company_profile": +0.2,
    "company_risk":    -1.0,
    "company_catalyst":+1.0,   # 若實際是 negative 再覆蓋
    "company_thesis":  +0.0,   # 依 side 再覆蓋
}
HALF_LIFE = {
    "company_profile": 90,
    "company_risk":    60,
    "company_catalyst":20,
    "company_thesis":  45,
}

def get_embeddings_model():
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def days_diff(a, b):
    return abs((a - b).days)

def cosine_topk(qv, k=5):
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
        cur.execute(sql, [vector_str, list(RESEARCH_TYPES), vector_str, k])
        return cur.fetchall()  # [(obj_type, obj_id, chunk_id, sim), ...]

def resolve_company(obj_type, obj_id):
    """
    由研究物件定位 company_id，以及補充 polarity（如 thesis/catalyst）
    """
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
            company_id = r.company_id
            polarity = -1.0
        except CompanyRisk.DoesNotExist:
            pass

    elif obj_type == "company_catalyst":
        try:
            c = CompanyCatalyst.objects.only("company_id","positive").get(id=obj_id)
            company_id = c.company_id
            polarity = +1.0 if c.positive else -1.0
        except CompanyCatalyst.DoesNotExist:
            pass

    elif obj_type == "company_thesis":
        try:
            t = CompanyThesis.objects.only("company_id","side").get(id=obj_id)
            company_id = t.company_id
            polarity = +0.5 if t.side == "for" else -0.5
        except CompanyThesis.DoesNotExist:
            pass

    return company_id, polarity

def get_news_vectors(news_id):
    Emb = get_embeddings_model()
    rows = Emb.objects.filter(object_type="news_chunk", object_id=news_id)\
                      .values_list("chunk_id","vector")
    return {cid: vec for (cid, vec) in rows}

class Command(BaseCommand):
    help = "Aggregate recent news→research matches into company-level signals with time decay and polarity."

    def add_arguments(self, parser):
        parser.add_argument("--days-back", type=int, default=7, help="Aggregate over the last N days of news")
        parser.add_argument("--topk-per-chunk", type=int, default=5, help="Top-K research hits per news chunk")
        parser.add_argument("--window-days", type=int, default=7, help="Signal window size to write (start..end)")
        parser.add_argument("--overwrite", action="store_true", help="Overwrite existing window entries")
        parser.add_argument("--min-sim", type=float, default=0.35, help="Ignore hits below this similarity")

    @transaction.atomic
    def handle(self, *args, **opts):
        days_back = opts["days_back"]
        topk = opts["topk_per_chunk"]
        window_days = opts["window_days"]
        overwrite = opts["overwrite"]
        min_sim = opts["min_sim"]

        now = timezone.now()
        since = now - timezone.timedelta(days=days_back)
        window_start = now - timezone.timedelta(days=window_days)
        window_end = now

        # 取最近新聞
        chunks = NewsChunk.objects.select_related("news")\
                    .filter(news__published_at__gte=since)\
                    .order_by("-news__published_at","idx")

        # 聚合容器
        agg_score = defaultdict(float)   # company_id -> score
        agg_details = defaultdict(list)  # company_id -> list of details
        news_by_company = defaultdict(lambda: defaultdict(float))  # company_id -> news_id -> |contrib| max

        # 主循環：對每個 chunk，用其已算向量做 topk 研究檢索
        for ch in chunks:
            vecs = get_news_vectors(ch.news_id)
            if ch.idx not in vecs:
                continue
            qv = vecs[ch.idx]

            for obj_type, obj_id, r_cid, sim in cosine_topk(qv, k=topk):
                if sim < min_sim:
                    continue

                company_id, polarity = resolve_company(obj_type, obj_id)
                if not company_id:
                    continue

                # 時間衰減
                dd = days_diff(now, ch.news.published_at)
                hl = HALF_LIFE.get(obj_type, 60)
                decay = 0.5 ** (dd / hl)

                contrib = float(sim) * float(polarity) * float(decay)

                agg_score[company_id] += contrib
                agg_details[company_id].append({
                    "news_id": ch.news_id,
                    "chunk_id": ch.idx,
                    "obj_type": obj_type,
                    "obj_id": obj_id,
                    "sim": float(sim),
                    "polarity": float(polarity),
                    "decay": float(decay),
                    "contrib": float(contrib),
                })
                # 記錄該新聞對公司的最大絕對貢獻（用於 top_news_ids）
                news_by_company[company_id][ch.news_id] = max(
                    news_by_company[company_id].get(ch.news_id, 0.0),
                    abs(contrib)
                )

        # 寫回 DB
        from reference.models import Company
        total = 0
        for cid, score in agg_score.items():
            # 取 top news ids（按 |contrib| 由大到小）
            news_scores = news_by_company[cid]
            top_news_ids = [nid for nid, _ in sorted(news_scores.items(), key=lambda x: x[1], reverse=True)[:10]]

            if overwrite:
                AnalyticsCompanySignal.objects.filter(
                    company_id=cid, window_start__lte=window_start, window_end__gte=window_end
                ).delete()

            obj, created = AnalyticsCompanySignal.objects.update_or_create(
                company_id=cid, window_start=window_start, window_end=window_end,
                defaults=dict(
                    score=score,
                    details_json=agg_details[cid],
                    top_news_ids=top_news_ids,
                )
            )
            total += 1

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Rolled up signals for {total} companies. Window={window_start.date()}..{window_end.date()}"
        ))