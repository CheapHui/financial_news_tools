# news/management/commands/link_news_entities.py
import os, re
from typing import Dict, List, Tuple
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import transaction, connection
from django.utils import timezone
from sentence_transformers import SentenceTransformer
import spacy

from news.models import NewsItem, NewsChunk, NewsEntity
from django.apps import apps as django_apps

EMBED_MODEL = os.getenv("EMBEDDING_MODEL","BAAI/bge-m3")  # 1024-d
DEVICE = os.getenv("EMBEDDING_DEVICE","cpu")
TOPK = int(os.getenv("EL_TOPK","8"))
ALPHA = float(os.getenv("EL_ALPHA","0.3"))   # lexical weight
BETA  = float(os.getenv("EL_BETA","0.7"))    # semantic weight
CTX = int(os.getenv("EL_CTX_WINDOW","120"))  # mention左右字符窗口
MIN_SCORE = float(os.getenv("EL_MIN_SCORE","0.35"))

_model = None
_nlp = None

def load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL, device=DEVICE)
    return _model

def load_spacy():
    """用小模型足夠（ORG 標籤）；將來可換 en_core_web_trf / HF pipeline。"""
    # en_core_web_sm 官方包含 NER，適合新聞文本，安裝: python -m spacy download en_core_web_sm
    # 亦可用 HF dslim/bert-base-NER 代替。 [oai_citation:4‡spacy.io](https://spacy.io/models?utm_source=chatgpt.com) [oai_citation:5‡huggingface.co](https://huggingface.co/dslim/bert-base-NER?utm_source=chatgpt.com)
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def norm(s:str)->str:
    return re.sub(r"[^A-Z0-9]+"," ", (s or "").upper()).strip()

def get_emb_model():
    from django.conf import settings
    path = getattr(settings,"EMBEDDINGS_MODEL","research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def context_window(text:str, start:int, end:int, w:int)->str:
    L = max(0, start-w); R = min(len(text), end+w)
    return text[L:R]

def pgvector_topk_cosine(qv:List[float], k:int=TOPK):
    """
    直接查通用 embeddings 表（company_*, industry_*），用 pgvector cosine (<=>) 排序。
    使用 HNSW 索引時會加速（見下方 SQL）。 [oai_citation:6‡GitHub](https://github.com/pgvector/pgvector?utm_source=chatgpt.com) [oai_citation:7‡Severalnines](https://severalnines.com/blog/vector-similarity-search-with-postgresqls-pgvector-a-deep-dive/?utm_source=chatgpt.com)
    """
    sql = """
    SELECT id, object_type, object_id, chunk_id, 1 - (vector <=> %s) AS sim
    FROM research_researchembedding
    WHERE object_type IN ('company_profile','company_risk','company_catalyst','company_thesis',
                          'industry_profile','industry_player')
    ORDER BY vector <=> %s
    LIMIT %s;
    """
    with connection.cursor() as cur:
        cur.execute(sql, [qv, qv, k])
        return cur.fetchall()  # [(id, obj_type, obj_id, chunk_id, sim), ...]

@transaction.atomic
def link_chunk(ch: NewsChunk, aliases: Dict[str,List[Tuple[str,int,float]]], EmbModel):
    text = ch.text
    nlp = load_spacy()
    doc = nlp(text)

    # 1) 從 NER + 字典生成候選 mentions
    mentions = []
    for ent in doc.ents:
        if ent.label_ != "ORG":  # 只要 ORG；有需要可加 PRODUCT
            continue
        key = norm(ent.text)
        if key in aliases:
            mentions.append((ent.text, ent.start_char, ent.end_char, key))
    # 補：簡單 ticker pattern（MVP）
    for m in set(re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z]{1,2})?\b", text)):
        key = norm(m)
        if key in aliases:
            idx = text.find(m)
            mentions.append((m, idx, idx+len(m), key))

    if not mentions:
        return 0

    # 2) 為每個 mention 取上下文→向量→pgvector 檢索→混合打分
    st = SentenceTransformer if False else None  # 閃避 IDE 提示
    sbert = load_model()
    written = 0
    seen_targets = set()

    for m_text, s, e, key in mentions:
        ctx = context_window(text, s, e, CTX)
        qv = sbert.encode([ctx], normalize_embeddings=True)[0].astype("float32").tolist()

        rows = pgvector_topk_cosine(qv, k=TOPK)
        sem_top = max((r[4] for r in rows), default=0.0)

        lex_top = max((w for (_,_,w) in aliases[key]), default=0.0)
        score = ALPHA*lex_top + BETA*sem_top
        if score < MIN_SCORE:
            continue

        # 取第一個 alias 作 target（簡化；如要 top-k 候選可擴充 NewsEntityCandidate）
        tgt_type, tgt_id, _ = aliases[key][0]
        if (tgt_type, tgt_id) in seen_targets:
            continue

        NewsEntity.objects.create(
            news=ch.news,
            text=m_text, start_char=s, end_char=e,
            norm=key, ticker=m_text if m_text.isupper() else "",
            target_type=tgt_type, target_id=tgt_id,
            score_lexical=float(lex_top), score_semantic=float(sem_top), score_final=float(score),
            method="hybrid",
        )
        seen_targets.add((tgt_type, tgt_id))
        written += 1

    return written

class Command(BaseCommand):
    help = "Link entities in recent news using spaCy NER + dictionary + pgvector ranking"

    def add_arguments(self, parser):
        parser.add_argument("--days-back", type=int, default=7)
        parser.add_argument("--limit", type=int, default=800)

    def handle(self, *args, **opts):
        since = timezone.now() - timezone.timedelta(days=opts["days_back"])
        qs = NewsChunk.objects.select_related("news").filter(
            news__published_at__gte=since
        ).order_by("-news__published_at","idx")[:opts["limit"]]

        aliases = cache.get("entity_aliases") or {}
        if not aliases:
            self.stderr.write(self.style.WARNING("Alias cache empty. Run: python manage.py build_entity_aliases"))
        Emb = get_emb_model()

        total=0
        for ch in qs:
            total += link_chunk(ch, aliases, Emb)
        self.stdout.write(self.style.SUCCESS(f"Linked entities written: {total}"))