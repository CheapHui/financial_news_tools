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
from news.views import news_matches
from analytics.views import company_signals, industry_signals

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/news/<int:news_id>/matches", news_matches, name="news-matches"),
    path("api/companies/<str:ticker>/signals", company_signals, name="company-signals"),
    path("api/industries/<int:id>/signals", industry_signals, name="industry-signals"),
]
