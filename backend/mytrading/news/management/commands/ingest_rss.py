# apps/news/management/commands/ingest_rss.py
import os, feedparser, httpx, traceback
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction, IntegrityError
from django.utils import timezone
from news.models import NewsItem, NewsChunk
from news.utils import extract_main_text, detect_lang, sha256_str, chunk_text

def _env_list(key: str, default=""):
    val = os.getenv(key, default)
    return [x.strip() for x in val.split(",") if x.strip()]

USER_AGENT = "Mozilla/5.0 (+news-ingestor)"
TIMEOUT = 20

class Command(BaseCommand):
    help = "Fetch RSS feeds, download articles, clean text, save NewsItem + chunks."

    def add_arguments(self, parser):
        parser.add_argument("--feed", action="append", help="RSS feed URL (can use multiple)")
        parser.add_argument("--max", type=int, default=50, help="Max entries per feed to attempt")
        parser.add_argument("--allow-langs", type=str, default=os.getenv("NEWS_ALLOWED_LANGS","en,zh"))

    @transaction.atomic
    def handle(self, *args, **opts):
        feeds = opts["feed"] or _env_list("NEWS_RSS_FEEDS")
        if not feeds:
            self.stdout.write(self.style.ERROR("No feeds provided. Use --feed or NEWS_RSS_FEEDS env."))
            return
        allow_langs = [x.strip() for x in (opts["allow_langs"] or "").split(",") if x.strip()]
        max_per = opts["max"]

        total_new = 0
        for feed_url in feeds:
            parsed = feedparser.parse(feed_url)
            domain = urlparse(feed_url).netloc or "feed"
            self.stdout.write(self.style.NOTICE(f"[Feed] {feed_url} -> {len(parsed.entries)} entries"))
            for i, e in enumerate(parsed.entries[:max_per]):
                url = e.get("link")
                title = (e.get("title") or "").strip()
                published = e.get("published_parsed") or e.get("updated_parsed")
                if not url or not title:
                    continue
                try:
                    published_at = timezone.make_aware(
                        timezone.datetime(*published[:6])
                    ) if published else timezone.now()

                    # 抓 HTML
                    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                        r = client.get(url, follow_redirects=True)
                        if r.status_code != 200:
                            continue
                        html = r.text

                    text = extract_main_text(html)
                    if not text:
                        continue

                    lang = detect_lang(text, fallback="en")
                    if allow_langs and lang not in allow_langs:
                        continue

                    checksum = sha256_str(url)

                    # 寫原文到 MinIO（django-storages）
                    key = f"news-raw/{published_at.date().isoformat()}/{checksum}.txt"
                    default_storage.save(key, ContentFile(text.encode("utf-8")))

                    # 入 NewsItem
                    try:
                        news = NewsItem.objects.create(
                            source=domain,
                            title=title,
                            url=url,
                            lang=lang,
                            published_at=published_at,
                            raw_text_location=key,
                            word_count=len(text.split()),
                            checksum=checksum,
                            status="ready",
                        )
                        total_new += 1
                    except IntegrityError:
                        # URL unique，已存在就略過
                        continue

                    # 切塊（先存 raw chunk 文字，embedding 由另一command做）
                    for idx, chunk in enumerate(chunk_text(text)):
                        NewsChunk.objects.create(
                            news=news, idx=idx, text=chunk, char_len=len(chunk)
                        )

                except Exception as ex:
                    self.stdout.write(self.style.ERROR(f"Error on {url}: {ex}"))
                    self.stdout.write(self.style.WARNING(traceback.format_exc()))
                    continue

        self.stdout.write(self.style.SUCCESS(f"Done. New articles: {total_new}"))