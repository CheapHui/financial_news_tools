from celery import shared_task
from django.core.management import call_command
from .utils import record_job, set_hnsw_ef_search
import io, json, re

STATS_RE = re.compile(r"STATS\s*(\{.*\})")

def _run_and_parse_stats(cmd_name, *cmd_args):
    buf = io.StringIO()
    call_command(cmd_name, stdout=buf, *cmd_args)
    processed = 0
    # 從輸出尾段找 STATS JSON
    for line in buf.getvalue().splitlines()[::-1]:
        m = STATS_RE.match(line.strip())
        if m:
            try:
                data = json.loads(m.group(1))
                # 優先讀 processed，否則累和
                if "processed" in data:
                    processed = int(data["processed"])
                else:
                    processed = int(sum(v for k,v in data.items() if isinstance(v,(int,float))))
            except Exception:
                processed = 0
            break
    return processed

@shared_task
def ingest_rss_task(max_items: int = 60):
    with record_job("ingest_rss") as setp:
        call_command("ingest_rss", "--max", str(max_items))  # 具體 feed 在 command 裡配置或用多 feed
        # 如你的 ingest_rss 有返回量可以改造回傳；暫用 0
        setp(0)

@shared_task
def embed_news_task(days_back: int = 3, limit: int = 1200):
    with record_job("embed_news") as setp:
        p = _run_and_parse_stats("embed_news", "--days-back", str(days_back), "--limit", str(limit))
        setp(p)

@shared_task
def build_aliases_task():
    with record_job("build_entity_aliases") as setp:
        call_command("build_entity_aliases")
        setp(1)

@shared_task
def link_entities_task(days_back: int = 3, limit: int = 1200, ef_search: int = 120):
    with record_job("link_news_entities") as setp:
        set_hnsw_ef_search(ef_search)
        p = _run_and_parse_stats("link_news_entities", "--days-back", str(days_back), "--limit", str(limit))
        setp(p)

@shared_task
def rollup_signals_task(days_back: int = 7, window_days: int = 7, topk: int = 5, ef_search: int = 120):
    with record_job("rollup_signals") as setp:
        set_hnsw_ef_search(ef_search)
        p = _run_and_parse_stats(
            "rollup_signals",
            "--days-back", str(days_back),
            "--window-days", str(window_days),
            "--topk-per-chunk", str(topk),
            "--industry-to-company", "weight",
            "--industry-top-n", "8",
            "--include-industry-signal"
        )
        setp(p)

