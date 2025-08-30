from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count
from ops.models import JobRun
from news.models import NewsItem, NewsChunk
from django.apps import apps as django_apps

def get_embeddings_model():
    from django.conf import settings
    path = getattr(settings, "EMBEDDINGS_MODEL", "research.ResearchEmbedding")
    app_label, model_name = path.split(".")
    return django_apps.get_model(app_label, model_name)

def metrics_summary(request):
    now = timezone.now()
    since = now - timezone.timedelta(days=1)
    Emb = get_embeddings_model()

    news_24h = NewsItem.objects.filter(published_at__gte=since).count()
    chunks_24h = NewsChunk.objects.filter(news__published_at__gte=since).count()
    embeds_total = Emb.objects.count()
    embeds_24h = Emb.objects.filter(created_at__gte=since).count() if hasattr(Emb, "created_at") else None

    jobs = list(
        JobRun.objects.filter(started_at__gte=since)
        .values("name")
        .annotate(runs=Count("id"))
        .order_by("name")
    )

    return JsonResponse({
        "now": now.isoformat(),
        "window_hours": 24,
        "news_24h": news_24h,
        "chunks_24h": chunks_24h,
        "embeddings_total": embeds_total,
        "embeddings_24h": embeds_24h,
        "jobs_24h": jobs,
    }, json_dumps_params={"ensure_ascii": False})