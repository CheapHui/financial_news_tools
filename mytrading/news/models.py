# apps/news/models.py
from django.db import models

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

    class Meta:
        indexes = [
            models.Index(fields=["published_at"]),
            models.Index(fields=["lang"]),
        ]
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