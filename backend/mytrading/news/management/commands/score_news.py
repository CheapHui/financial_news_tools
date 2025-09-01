from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from news.models import NewsItem
from news.news_scoring import score_news_item

class Command(BaseCommand):
    help = "Score linked NewsItem via DeepSeek and store JSON to news_scores_json"

    def add_arguments(self, parser):
        parser.add_argument("--since-hours", type=int, default=24)
        parser.add_argument("--model", type=str, default="deepseek-reasoner")
        parser.add_argument("--half-life", type=int, default=72)
        parser.add_argument("--force", action="store_true", help="re-score even if already scored")

    def handle(self, *args, **opts):
        since = timezone.now() - timezone.timedelta(hours=opts["since_hours"])

        # 條件：最近 N 小時、有內容，且已完成 link（有關聯到公司/行業）
        qs = (
            NewsItem.objects
            .filter(
                Q(published_at__gte=since) | Q(scores_updated_at__isnull=True),
                Q(title__isnull=False),  # NewsItem 只有 title 字段，沒有 body
            )
            .order_by("published_at")
        )

        processed = 0
        skipped = 0
        for item in qs.iterator():
            if item.news_scores_json and not opts["force"]:
                skipped += 1
                continue

            # 讀多對多（若你模型名不同請調整）
            tickers = [t.ticker for t in getattr(item, "tickers").all()] if hasattr(item, "tickers") else []
            industries = [i.name for i in getattr(item, "industries").all()] if hasattr(item, "industries") else []

            body = item.title or ""  # NewsItem 只有 title 字段
            if not body.strip():
                skipped += 1
                continue

            try:
                payload = score_news_item(
                    item_id=str(item.id),
                    body=body,
                    source_url=item.url,  # NewsItem 使用 url 字段而不是 source_url
                    published_at=item.published_at,
                    tickers=tickers,
                    industries=industries,
                    model=opts["model"],
                    half_life_hours=opts["half_life"],
                )
                item.mark_scored(payload)
                processed += 1
            except Exception as e:
                self.stderr.write(f"[score_news:skip] id={item.id} err={e}")

        self.stdout.write(self.style.SUCCESS(f"processed={processed} skipped={skipped}"))