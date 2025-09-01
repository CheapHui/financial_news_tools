from django.urls import path
from .views import EmbeddingEvalView, EmbeddingQualityView, QuickEvalView

urlpatterns = [
    path("embedding", EmbeddingEvalView.as_view(), name="embedding-eval"),
    path("quality", EmbeddingQualityView.as_view(), name="embedding-quality"),
    path("quick", QuickEvalView.as_view(), name="quick-eval"),
]