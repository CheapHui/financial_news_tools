# news/models.py
from django.db import models
from pgvector.django import VectorField

class NewsEmbedding(models.Model):
    model_name = models.CharField(max_length=64)
    dim = models.PositiveIntegerField()
    vector = VectorField(dimensions=1024)  # 依你實際 embedding 維度
    created_at = models.DateTimeField(auto_now_add=True)