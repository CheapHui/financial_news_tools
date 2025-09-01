from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from analytics.models import AnalyticsRecommendation

class TopRecommendationsView(APIView):
    def get(self, request):
        d = request.GET.get("date")
        topn = int(request.GET.get("n", 50))
        if d:
            asof = d
        else:
            asof = timezone.now().date()
        qs = (AnalyticsRecommendation.objects
              .filter(as_of_date=asof)
              .order_by("rank")[:topn])
        data = [{
            "ticker": rec.company.ticker,
            "as_of": str(rec.as_of_date),
            "rank": rec.rank,
            "final": float(rec.final_score),
            "rs": float(rec.rs_score),
            "stage2": rec.stage2_pass,
            "news_w": float(rec.news_weight_factor),
        } for rec in qs]
        return Response({"date": str(asof), "count": len(data), "items": data})