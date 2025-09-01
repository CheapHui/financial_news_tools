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


@require_GET
def signals_summary(request):
    """
    GET /api/signals/summary
    返回最新的信號匯總，包括：
    - 公司信號排行榜 (top positive/negative)
    - 行業信號排行榜
    - 統計信息
    Query params:
      - limit: int (default 20) 每類排行榜的數量
      - days_back: int (default 7) 只看最近N天的窗口
    """
    from django.utils import timezone
    from django.db.models import Count, Avg, Max
    
    try:
        limit = int(request.GET.get("limit", "20"))
        limit = max(1, min(limit, 100))
    except Exception:
        limit = 20
        
    try:
        days_back = int(request.GET.get("days_back", "7"))
        days_back = max(1, min(days_back, 30))
    except Exception:
        days_back = 7
    
    # 時間範圍
    now = timezone.now()
    cutoff = now - timezone.timedelta(days=days_back)
    
    # 公司信號排行榜 - 最正面
    top_positive_companies = (
        AnalyticsCompanySignal.objects
        .select_related("company")
        .filter(window_end__gte=cutoff, score__gt=0)
        .order_by("-score")[:limit]
    )
    
    # 公司信號排行榜 - 最負面
    top_negative_companies = (
        AnalyticsCompanySignal.objects
        .select_related("company")
        .filter(window_end__gte=cutoff, score__lt=0)
        .order_by("score")[:limit]
    )
    
    # 行業信號排行榜 - 最正面
    top_positive_industries = (
        AnalyticsIndustrySignal.objects
        .select_related("industry")
        .filter(window_end__gte=cutoff, score__gt=0)
        .order_by("-score")[:limit]
    )
    
    # 行業信號排行榜 - 最負面  
    top_negative_industries = (
        AnalyticsIndustrySignal.objects
        .select_related("industry")
        .filter(window_end__gte=cutoff, score__lt=0)
        .order_by("score")[:limit]
    )
    
    # 統計信息
    company_stats = AnalyticsCompanySignal.objects.filter(window_end__gte=cutoff).aggregate(
        total=Count("id"),
        positive_count=Count("id", filter=Q(score__gt=0)),
        negative_count=Count("id", filter=Q(score__lt=0)),
        avg_score=Avg("score"),
        max_positive=Max("score", filter=Q(score__gt=0)),
        max_negative=Max("score", filter=Q(score__lt=0))
    )
    
    industry_stats = AnalyticsIndustrySignal.objects.filter(window_end__gte=cutoff).aggregate(
        total=Count("id"),
        positive_count=Count("id", filter=Q(score__gt=0)),
        negative_count=Count("id", filter=Q(score__lt=0)),
        avg_score=Avg("score"),
        max_positive=Max("score", filter=Q(score__gt=0)),
        max_negative=Max("score", filter=Q(score__lt=0))
    )
    
    def serialize_company_signal(sig):
        return {
            "ticker": sig.company.ticker,
            "company_name": sig.company.name,
            "company_id": sig.company.id,
            "score": round(float(sig.score), 4),
            "window_start": sig.window_start.isoformat(),
            "window_end": sig.window_end.isoformat(),
            "top_news_count": len(sig.top_news_ids or []),
            "updated_at": sig.updated_at.isoformat(),
        }
    
    def serialize_industry_signal(sig):
        return {
            "industry_name": sig.industry.name,
            "industry_id": sig.industry.id,
            "score": round(float(sig.score), 4),
            "window_start": sig.window_start.isoformat(),
            "window_end": sig.window_end.isoformat(),
            "top_news_count": len(sig.top_news_ids or []),
            "updated_at": sig.updated_at.isoformat(),
        }
    
    payload = {
        "summary": {
            "query_params": {
                "limit": limit,
                "days_back": days_back,
                "cutoff_date": cutoff.isoformat(),
            },
            "company_stats": {
                "total_signals": company_stats["total"] or 0,
                "positive_signals": company_stats["positive_count"] or 0,
                "negative_signals": company_stats["negative_count"] or 0,
                "avg_score": round(float(company_stats["avg_score"] or 0), 4),
                "max_positive_score": round(float(company_stats["max_positive"] or 0), 4),
                "max_negative_score": round(float(company_stats["max_negative"] or 0), 4),
            },
            "industry_stats": {
                "total_signals": industry_stats["total"] or 0,
                "positive_signals": industry_stats["positive_count"] or 0,
                "negative_signals": industry_stats["negative_count"] or 0,
                "avg_score": round(float(industry_stats["avg_score"] or 0), 4),
                "max_positive_score": round(float(industry_stats["max_positive"] or 0), 4),
                "max_negative_score": round(float(industry_stats["max_negative"] or 0), 4),
            },
        },
        "rankings": {
            "top_positive_companies": [serialize_company_signal(s) for s in top_positive_companies],
            "top_negative_companies": [serialize_company_signal(s) for s in top_negative_companies],
            "top_positive_industries": [serialize_industry_signal(s) for s in top_positive_industries],
            "top_negative_industries": [serialize_industry_signal(s) for s in top_negative_industries],
        }
    }
    
    return JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})


@require_GET
def news_score_signals_summary(request):
    """
    GET /api/signals/news-score-summary/
    返回基於新聞分數的信號匯總，包括：
    - 公司和行業的新聞分數排行榜
    - 統計信息
    Query params:
      - limit: int (default 20) 每類排行榜的數量
      - lookback_hours: int (default 168) 回看時間（小時）
    """
    from django.utils import timezone
    from django.db.models import Count, Avg, Max, Min
    
    try:
        limit = int(request.GET.get("limit", "20"))
        limit = max(1, min(limit, 100))
    except Exception:
        limit = 20
        
    try:
        lookback_hours = int(request.GET.get("lookback_hours", "168"))  # 默認7天
        lookback_hours = max(1, min(lookback_hours, 720))  # 最大30天
    except Exception:
        lookback_hours = 168
    
    # 時間範圍
    now = timezone.now()
    cutoff = now - timezone.timedelta(hours=lookback_hours)
    
    # 公司新聞分數排行榜 - 最高分
    top_positive_companies = (
        AnalyticsCompanySignal.objects
        .select_related("company")
        .filter(last_aggregated_at__gte=cutoff, window_score__gt=0, window_count__gt=0)
        .order_by("-window_score")[:limit]
    )
    
    # 公司新聞分數排行榜 - 最低分
    top_negative_companies = (
        AnalyticsCompanySignal.objects
        .select_related("company")
        .filter(last_aggregated_at__gte=cutoff, window_score__lt=0, window_count__gt=0)
        .order_by("window_score")[:limit]
    )
    
    # 行業新聞分數排行榜 - 最高分
    top_positive_industries = (
        AnalyticsIndustrySignal.objects
        .select_related("industry")
        .filter(last_aggregated_at__gte=cutoff, window_score__gt=0, window_count__gt=0)
        .order_by("-window_score")[:limit]
    )
    
    # 行業新聞分數排行榜 - 最低分
    top_negative_industries = (
        AnalyticsIndustrySignal.objects
        .select_related("industry")
        .filter(last_aggregated_at__gte=cutoff, window_score__lt=0, window_count__gt=0)
        .order_by("window_score")[:limit]
    )
    
    # 統計信息
    company_stats = AnalyticsCompanySignal.objects.filter(
        last_aggregated_at__gte=cutoff, window_count__gt=0
    ).aggregate(
        total=Count("id"),
        positive_count=Count("id", filter=Q(window_score__gt=0)),
        negative_count=Count("id", filter=Q(window_score__lt=0)),
        avg_score=Avg("window_score"),
        max_positive=Max("window_score", filter=Q(window_score__gt=0)),
        max_negative=Min("window_score", filter=Q(window_score__lt=0)),
        total_news_count=Avg("window_count")
    )
    
    industry_stats = AnalyticsIndustrySignal.objects.filter(
        last_aggregated_at__gte=cutoff, window_count__gt=0
    ).aggregate(
        total=Count("id"),
        positive_count=Count("id", filter=Q(window_score__gt=0)),
        negative_count=Count("id", filter=Q(window_score__lt=0)),
        avg_score=Avg("window_score"),
        max_positive=Max("window_score", filter=Q(window_score__gt=0)),
        max_negative=Min("window_score", filter=Q(window_score__lt=0)),
        total_news_count=Avg("window_count")
    )
    
    def serialize_company_news_signal(sig):
        return {
            "ticker": sig.company.ticker,
            "company_name": sig.company.name,
            "company_id": sig.company.id,
            "window_score": float(sig.window_score),
            "window_count": sig.window_count,
            "avg_score_per_news": float(sig.window_score) / max(sig.window_count, 1),
            "last_aggregated_at": sig.last_aggregated_at.isoformat() if sig.last_aggregated_at else None,
            "created_at": sig.created_at.isoformat(),
            "updated_at": sig.updated_at.isoformat(),
        }
    
    def serialize_industry_news_signal(sig):
        return {
            "industry_name": sig.industry.name,
            "industry_id": sig.industry.id,
            "window_score": float(sig.window_score),
            "window_count": sig.window_count,
            "avg_score_per_news": float(sig.window_score) / max(sig.window_count, 1),
            "last_aggregated_at": sig.last_aggregated_at.isoformat() if sig.last_aggregated_at else None,
            "created_at": sig.created_at.isoformat(),
            "updated_at": sig.updated_at.isoformat(),
        }
    
    payload = {
        "summary": {
            "query_params": {
                "limit": limit,
                "lookback_hours": lookback_hours,
                "cutoff_date": cutoff.isoformat(),
            },
            "company_stats": {
                "total_signals": company_stats["total"] or 0,
                "positive_signals": company_stats["positive_count"] or 0,
                "negative_signals": company_stats["negative_count"] or 0,
                "avg_window_score": round(float(company_stats["avg_score"] or 0), 6),
                "max_positive_score": round(float(company_stats["max_positive"] or 0), 6),
                "max_negative_score": round(float(company_stats["max_negative"] or 0), 6),
                "avg_news_count": round(float(company_stats["total_news_count"] or 0), 1),
            },
            "industry_stats": {
                "total_signals": industry_stats["total"] or 0,
                "positive_signals": industry_stats["positive_count"] or 0,
                "negative_signals": industry_stats["negative_count"] or 0,
                "avg_window_score": round(float(industry_stats["avg_score"] or 0), 6),
                "max_positive_score": round(float(industry_stats["max_positive"] or 0), 6),
                "max_negative_score": round(float(industry_stats["max_negative"] or 0), 6),
                "avg_news_count": round(float(industry_stats["total_news_count"] or 0), 1),
            },
        },
        "rankings": {
            "top_positive_companies": [serialize_company_news_signal(s) for s in top_positive_companies],
            "top_negative_companies": [serialize_company_news_signal(s) for s in top_negative_companies],
            "top_positive_industries": [serialize_industry_news_signal(s) for s in top_positive_industries],
            "top_negative_industries": [serialize_industry_news_signal(s) for s in top_negative_industries],
        }
    }
    
    return JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})


@require_GET
def company_news_score_signal(request, ticker: str):
    """
    GET /api/companies/<ticker>/news-score-signal/
    返回特定公司的新聞分數信號詳情
    """
    tkr = ticker.strip().upper()

    try:
        company = Company.objects.get(ticker__iexact=tkr)
    except Company.DoesNotExist:
        raise Http404("company not found")

    # 取該公司的新聞分數信號
    sig = (AnalyticsCompanySignal.objects
           .filter(company=company, window_count__gt=0)
           .order_by("-last_aggregated_at")
           .first())
           
    if not sig:
        return JsonResponse({
            "ticker": company.ticker,
            "company_id": company.id,
            "name": company.name,
            "news_score_signal": None,
            "message": "no news score signal found for this company"
        }, status=200, json_dumps_params={"ensure_ascii": False})

    # 獲取相關新聞（如果有 top_news_ids）
    related_news = []
    if sig.top_news_ids:
        news_qs = NewsItem.objects.filter(id__in=sig.top_news_ids).only(
            "id", "title", "url", "published_at", "news_scores_json"
        )
        for news in news_qs:
            news_data = {
                "id": news.id,
                "title": news.title,
                "url": news.url,
                "published_at": news.published_at.isoformat(),
            }
            # 添加新聞分數信息
            if news.news_scores_json:
                scores = news.news_scores_json.get("scores", {})
                news_data.update({
                    "impact_score": scores.get("impact_score", 0.0),
                    "credibility_score": scores.get("credibility_score", 0.0),
                    "novelty_score": scores.get("novelty_score", 0.0),
                    "decayed_weight": scores.get("decayed_weight", 1.0),
                    "sentiment_overall": news.news_scores_json.get("sentiment_overall", 0.0),
                })
            related_news.append(news_data)

    payload = {
        "ticker": company.ticker,
        "company_id": company.id,
        "name": company.name,
        "news_score_signal": {
            "window_score": float(sig.window_score),
            "window_count": sig.window_count,
            "avg_score_per_news": float(sig.window_score) / max(sig.window_count, 1),
            "last_aggregated_at": sig.last_aggregated_at.isoformat() if sig.last_aggregated_at else None,
            "created_at": sig.created_at.isoformat(),
            "updated_at": sig.updated_at.isoformat(),
            "related_news": related_news,
            # 同時提供原有的研究匹配信號（如果有）
            "research_signal": {
                "score": sig.score,
                "window_start": sig.window_start.isoformat() if sig.window_start else None,
                "window_end": sig.window_end.isoformat() if sig.window_end else None,
                "top_news_ids": sig.top_news_ids,
            } if sig.score != 0 else None,
        },
    }
    return JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})