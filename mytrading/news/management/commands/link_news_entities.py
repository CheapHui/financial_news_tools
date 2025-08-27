# news/management/commands/link_news_entities.py
import re, os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.cache import cache
from news.models import NewsItem, NewsChunk, NewsEntity
from django.utils import timezone
from sentence_transformers import SentenceTransformer
from django.apps import apps as django_apps

EMBED_MODEL = os.getenv("EMBEDDING_MODEL","BAAI/bge-m3")
DEVICE = os.getenv("EMBEDDING_DEVICE","cpu")
model = SentenceTransformer(EMBED_MODEL, device=DEVICE)

def normalize(s:str)->str:
    return re.sub(r"[^A-Z0-9]+"," ", (s or "").upper()).strip()

def get_emb_model():
    from django.conf import settings
    path = getattr(settings,"EMBEDDINGS_MODEL","research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def bm25_like(mention:str, alias_weight:float)->float:
    # MVP：字典命中即賦一個權重分；將來可換成真正 BM25（Elastic/OpenSearch）
    return alias_weight

@transaction.atomic
def link_one_chunk(ch, aliases, Emb):
    text = ch.text
    # 1) 簡單規則抽 mention（MVP：找大寫Ticker/公司關鍵詞；可換成 spaCy/HF NER）：
    #   建議日後用 dslim/bert-base-NER 或 spaCy 英文新聞管線抽 ORG 實體。 [oai_citation:15‡huggingface.co](https://huggingface.co/dslim/bert-base-NER?utm_source=chatgpt.com) [oai_citation:16‡spacy.io](https://spacy.io/usage/spacy-101?utm_source=chatgpt.com)
    candidates = []
    tokens = re.findall(r"[A-Za-z0-9\.\-]{2,}", text)
    window = 80
    for m in set(tokens):
        key = normalize(m)
        if key in aliases:
            ctx = extract_ctx(text, m, window)
            # 2) 計 semantic 分（新聞上下文向量 → 研究庫）
            qv = model.encode([ctx], normalize_embeddings=True)[0].astype("float32").tolist()
            # 將 Python list 轉換為 PostgreSQL vector 格式
            vector_str = '[' + ','.join(map(str, qv)) + ']'
            # pgvector 檢索：這裡用 ORM.Raw SQL（示例）
            from django.db import connection
            sql = """
            SELECT id, object_type, object_id, 1 - (vector <=> %s::vector) AS sim
            FROM research_researchembedding
            WHERE object_type IN ('company_profile','company_risk','company_catalyst',
                                  'company_thesis','industry_profile','industry_player')
            ORDER BY vector <=> %s::vector LIMIT 5;
            """
            with connection.cursor() as cur:
                cur.execute(sql, [vector_str, vector_str])
                rows = cur.fetchall()
            sem_top = max([r[3] for r in rows], default=0.0)

            # 3) lexical 分（字典 weight 最大者）
            lex_top = max([w for (_,_,w) in aliases[key]], default=0.0)

            score = 0.3*lex_top + 0.7*sem_top
            # 取第一個別名對象作 target（MVP；可擴展多候選）
            tgt_type, tgt_id, _ = aliases[key][0]
            candidates.append((m, ctx, tgt_type, tgt_id, lex_top, sem_top, score))

    # 4) 取 top1 寫入 DB（同一 target 避免重覆）
    written = 0
    seen = set()
    for m, ctx, ttype, tid, slex, ssem, s in sorted(candidates, key=lambda x: x[-1], reverse=True):
        if (ttype, tid) in seen: continue
        span = find_span(text, m)
        NewsEntity.objects.create(
            news=ch.news, text=m, start_char=span[0], end_char=span[1],
            norm=normalize(m), ticker=m if m.isupper() else "",
            target_type=ttype, target_id=tid,
            score_lexical=float(slex), score_semantic=float(ssem), score_final=float(s),
            method="hybrid",
        )
        seen.add((ttype, tid)); written += 1
    return written

def extract_ctx(text, mention, window):
    # 取 mention 左右 window chars
    idx = text.lower().find(mention.lower())
    if idx < 0: return text[:min(len(text), 2*window)]
    start = max(0, idx-window); end = min(len(text), idx+len(mention)+window)
    return text[start:end]

def find_span(text, mention):
    i = text.lower().find(mention.lower())
    return (max(0,i), max(0,i)+len(mention)) if i>=0 else (0,0)

class Command(BaseCommand):
    help = "Link entities in recent news chunks via dictionary+vector hybrid and write to news_entities."

    def add_arguments(self, parser):
        parser.add_argument("--days-back", type=int, default=7)
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args, **opts):
        from django.utils import timezone
        since = timezone.now() - timezone.timedelta(days=opts["days_back"])
        qs = NewsChunk.objects.select_related("news").filter(news__published_at__gte=since).order_by("-news__published_at")[:opts["limit"]]
        aliases = cache.get("entity_aliases") or {}
        Emb = get_emb_model()

        total=0
        for ch in qs:
            total += link_one_chunk(ch, aliases, Emb)
        self.stdout.write(self.style.SUCCESS(f"Linked entities written: {total}"))