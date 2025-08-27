from django.db import models
from reference.models import Company, Industry

class AnalyticsIndustrySignal(models.Model):
    """
    某時間窗（window）內，由新聞×研究匹配聚合的行業級信號分數
    """
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="signals")
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    score = models.FloatField(default=0.0)
    details_json = models.JSONField(default=list)   # [{news_id, chunk_id, obj_type, obj_id, sim, contrib, decay}]
    top_news_ids = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["industry", "window_end"]),
            models.Index(fields=["window_start", "window_end"]),
        ]
        unique_together = [("industry", "window_start", "window_end")]

    def __str__(self):
        return f"{self.industry.name} {self.window_start.date()}–{self.window_end.date()} score={self.score:.3f}"