from django.db import models
from pgvector.django import VectorField

class VectorProbe(models.Model):
    title = models.CharField(max_length=100)
    vector = VectorField(dimensions=3)  # 測試用3維
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title