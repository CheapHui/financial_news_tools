# research/models_embeddings.py
from django.db import models
from pgvector.django import VectorField

class ResearchEmbedding(models.Model):
    object_type = models.CharField(max_length=40)   # 'company_profile' | 'company_risk' | ...
    object_id = models.IntegerField()               # 對應原表主鍵
    chunk_id = models.IntegerField(default=0)       # 如需切塊
    model_name = models.CharField(max_length=64)
    dim = models.IntegerField()
    vector = VectorField(dimensions=1024)
    meta = models.JSONField(default=dict)           # {"company_id": 1, "year": 2024, "field": "description"}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
        ]