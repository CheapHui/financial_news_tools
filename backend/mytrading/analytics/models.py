from django.db import models
from reference.models import Industry
from django.utils import timezone

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

    # 新聞分數聚合字段
    window_score = models.DecimalField(max_digits=12, decimal_places=6, default=0.0)  # 基於新聞分數的窗口分數
    window_count = models.IntegerField(default=0)  # 參與計算的新聞數量
    last_aggregated_at = models.DateTimeField(null=True, blank=True)  # 最後聚合時間

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
    

class AnalyticsRecommendation(models.Model):
    company = models.ForeignKey("reference.Company", on_delete=models.CASCADE, db_index=True)
    as_of_date = models.DateField(db_index=True)

    # RS 分解
    rs_score = models.DecimalField(max_digits=6, decimal_places=2)  # 0~100（百分位）
    rs_p1m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rs_p3m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rs_p6m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rs_method = models.CharField(max_length=50, default="percentile_relret_1/3/6m_wt=0.2/0.3/0.5")

    # Stage 2
    stage2_pass = models.BooleanField(default=False)
    stage2_reasons = models.JSONField(null=True, blank=True)  # 存各條件 true/false

    # 新聞權重（已 rollup 過）
    news_window_score = models.DecimalField(max_digits=16, decimal_places=6, default=0)  # 你 rollup 的 window_score（可為負）
    news_weight_factor = models.DecimalField(max_digits=6, decimal_places=3, default=1)  # 1 + α * tanh(k*score)

    # 綜合分
    final_score = models.DecimalField(max_digits=7, decimal_places=3, db_index=True)  # 0~100（clip）
    rank = models.IntegerField(db_index=True)

    details = models.JSONField(null=True, blank=True)  # 例如移動平均價、52W 高低、原始回報等
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("company", "as_of_date")
        indexes = [
            models.Index(fields=["as_of_date", "final_score"]),
            models.Index(fields=["as_of_date", "rank"]),
        ]