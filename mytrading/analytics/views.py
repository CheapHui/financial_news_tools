# apps/analytics/views.py
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from reference.models import Company, Industry
from research.models import AnalyticsCompanySignal
from analytics.models import AnalyticsIndustrySignal
from news.models import NewsItem

def _lower(s): return (s or "").strip().lower()

@require_GET
def company_signals(request, ticker: str):
    """
    GET /api/companies/<ticker>/signals
    Query params:
      - max_details: int (default 100)  # 限制 details_json 條數（避免 payload 過大）
    """
    tkr = ticker.strip().upper()

    try:
        company = Company.objects.get(ticker__iexact=tkr)
    except Company.DoesNotExist:
        raise Http404("company not found")

    # 取該公司的「最新窗口」信號
    sig = (AnalyticsCompanySignal.objects
           .filter(company=company)
           .order_by("-window_end", "-updated_at")
           .first())
    if not sig:
        # 沒有任何信號，仍返回公司基本資料
        return JsonResponse({
            "ticker": company.ticker,
            "company_id": company.id,
            "name": company.name,
            "signal": None,
            "message": "no signal found for this company"
        }, status=200, json_dumps_params={"ensure_ascii": False})

    # 限制 details 條數（避免一次性返回過多）
    try:
        max_details = int(request.GET.get("max_details", "100"))
        max_details = max(1, min(max_details, 2000))
    except Exception:
        max_details = 100

    details = sig.details_json or []
    if max_details and len(details) > max_details:
        details = details[:max_details]

    # 把 top_news_ids 解析成新聞摘要
    news_map = {}
    if sig.top_news_ids:
        qs = NewsItem.objects.filter(id__in=sig.top_news_ids).only("id","title","url","published_at")
        for n in qs:
            news_map[n.id] = {
                "id": n.id,
                "title": n.title,
                "url": n.url,
                "published_at": n.published_at.isoformat(),
            }
    top_news = [news_map[nid] for nid in sig.top_news_ids if nid in news_map]

    payload = {
        "ticker": company.ticker,
        "company_id": company.id,
        "name": company.name,
        "signal": {
            "score": sig.score,
            "window_start": sig.window_start.isoformat(),
            "window_end": sig.window_end.isoformat(),
            "top_news_ids": sig.top_news_ids,
            "top_news": top_news,              # 方便前端直接顯示
            "details": details,                # [{news_id, chunk_id, obj_type, obj_id, sim, polarity, decay, contrib}]
            "updated_at": sig.updated_at.isoformat(),
        },
    }
    return JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})



@require_GET
def industry_signals(request, id: int):
    """
    GET /api/industries/<id>/signals
    Query params:
      - max_details: int (default 100)  # 限制 details_json 條數，避免 payload 過大
    """
    try:
        industry = Industry.objects.get(id=id)
    except Industry.DoesNotExist:
        raise Http404("industry not found")

    sig = (AnalyticsIndustrySignal.objects
           .filter(industry=industry)
           .order_by("-window_end", "-updated_at")
           .first())

    if not sig:
        return JsonResponse({
            "industry_id": industry.id,
            "industry": industry.name,
            "signal": None,
            "message": "no signal found for this industry"
        }, status=200, json_dumps_params={"ensure_ascii": False})

    # 參數：限制 details 條數
    try:
        max_details = int(request.GET.get("max_details", "100"))
        max_details = max(1, min(max_details, 2000))
    except Exception:
        max_details = 100

    details = sig.details_json or []
    if max_details and len(details) > max_details:
        details = details[:max_details]

    # 將 top_news_ids 解成新聞摘要
    news_map = {}
    if sig.top_news_ids:
        qs = NewsItem.objects.filter(id__in=sig.top_news_ids).only("id","title","url","published_at")
        for n in qs:
            news_map[n.id] = {
                "id": n.id,
                "title": n.title,
                "url": n.url,
                "published_at": n.published_at.isoformat(),
            }
    top_news = [news_map[nid] for nid in sig.top_news_ids if nid in news_map]

    payload = {
        "industry_id": industry.id,
        "industry": industry.name,
        "signal": {
            "score": sig.score,
            "window_start": sig.window_start.isoformat(),
            "window_end": sig.window_end.isoformat(),
            "top_news_ids": sig.top_news_ids,
            "top_news": top_news,
            "details": details,
            "updated_at": sig.updated_at.isoformat(),
        },
    }
    return JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})