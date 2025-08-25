from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Sector(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    source = models.CharField(max_length=40, default="custom", help_text="e.g. GICS, custom")
    def __str__(self): return self.name

class Industry(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, related_name="industries")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return self.name

class Company(TimeStampedModel):
    ticker = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    exchange = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=2, default="US")
    sector = models.ForeignKey(Sector, null=True, on_delete=models.SET_NULL)
    industry = models.ForeignKey(Industry, null=True, on_delete=models.SET_NULL)
    market_cap = models.BigIntegerField(null=True, blank=True)  # USD
    shares_outstanding = models.BigIntegerField(null=True, blank=True)
    cik = models.CharField(max_length=20, blank=True, default="")
    isin = models.CharField(max_length=12, blank=True, default="")
    website = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["ticker"]),
            models.Index(fields=["name"]),
            models.Index(fields=["industry"]),
        ]
    def __str__(self): return f"{self.ticker} - {self.name}"