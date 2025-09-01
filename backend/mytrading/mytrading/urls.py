"""
URL configuration for mytrading project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from news.views import news_matches, analyze_url
from analytics.views import company_signals, industry_signals, signals_summary, news_score_signals_summary, company_news_score_signal
from ops.views import metrics_summary
from django.urls import include
from api.views import TopRecommendationsView
from api.pipeline_views import (
    start_pipeline, pipeline_status_api, stop_pipeline, clear_pipeline_logs
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/news/<int:news_id>/matches/", news_matches, name="news-matches"),
    path("api/news/analyze-url/", analyze_url, name="analyze-url"),
    path("api/companies/<str:ticker>/signals/", company_signals, name="company-signals"),
    path("api/industries/<int:id>/signals/", industry_signals, name="industry-signals"),
    path("api/signals/summary/", signals_summary, name="signals-summary"),
    path("api/signals/news-score-summary/", news_score_signals_summary, name="news-score-signals-summary"),
    path("api/companies/<str:ticker>/news-score-signal/", company_news_score_signal, name="company-news-score-signal"),
    path("api/metrics/summary/", metrics_summary, name="metrics-summary"),
    path("api/evals/", include("evals.urls")),
    path("api/recommendations/", TopRecommendationsView.as_view(), name="top-recommendations"),
    path("api/pipeline/start/", start_pipeline, name="pipeline-start"),
    path("api/pipeline/status/", pipeline_status_api, name="pipeline-status"),
    path("api/pipeline/stop/", stop_pipeline, name="pipeline-stop"),
    path("api/pipeline/clear-logs/", clear_pipeline_logs, name="pipeline-clear-logs"),
]
