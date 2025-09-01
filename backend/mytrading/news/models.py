# apps/news/models.py
from django.db import models
from pgvector.django import VectorField
from django.db import models
from django.utils import timezone
from django.contrib.postgres.indexes import GinIndex

class NewsItem(models.Model):
    source = models.CharField(max_length=100)
    title = models.TextField()
    url = models.URLField(unique=True)
    lang = models.CharField(max_length=8, default="en")
    published_at = models.DateTimeField()
    ingested_at = models.DateTimeField(auto_now_add=True)
    raw_text_location = models.CharField(max_length=300, blank=True, default="")  # s3:// or / key
    word_count = models.IntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=20, default="ready")  # ready/errored
    news_scores_json = models.JSONField(null=True, blank=True)
    scores_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["published_at"]),
            models.Index(fields=["lang"]),
            GinIndex(
            name="idx_news_scores_json_gin",
            fields=["news_scores_json"],)
        ]

    def mark_scored(self, payload: dict):
        self.news_scores_json = payload
        self.scores_updated_at = timezone.now()
        self.save(update_fields=["news_scores_json", "scores_updated_at"])

    def __str__(self):
        return self.title


class NewsChunk(models.Model):
    news = models.ForeignKey(NewsItem, on_delete=models.CASCADE, related_name="chunks")
    idx = models.IntegerField()               # chunk index
    text = models.TextField()
    char_len = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("news", "idx")]
        indexes = [models.Index(fields=["news"])]

class NewsEntity(models.Model):
    """
    一條新聞內抽到的「一個 mention + 已連結到的 target」。
    target 可對應 Company/Industry/IndustryPlayer（以 object_type + object_id 表示）
    """
    news = models.ForeignKey(NewsItem, on_delete=models.CASCADE, related_name="entities")
    # mention span
    text = models.CharField(max_length=256)               # 原文片段，例如 "TSMC", "Taiwan Semiconductor"
    start_char = models.IntegerField()
    end_char = models.IntegerField()
    # 正規化 / 字典
    norm = models.CharField(max_length=256, blank=True, default="")     # 標準化名稱（如 "TAIWAN SEMICONDUCTOR"）
    ticker = models.CharField(max_length=24, blank=True, default="")    # 若能判到
    # 連結對象（研究庫內目標）
    target_type = models.CharField(max_length=40)         # 'company' | 'industry' | 'industry_player'
    target_id = models.IntegerField()
    # 相似度與來源
    score_lexical = models.FloatField(default=0.0)        # BM25/字典命中分
    score_semantic = models.FloatField(default=0.0)       # 向量相似
    score_final = models.FloatField(default=0.0)          # 混合分
    method = models.CharField(max_length=40, default="hybrid")  # 'lexical'|'semantic'|'hybrid'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["news"]), models.Index(fields=["target_type","target_id"])]




