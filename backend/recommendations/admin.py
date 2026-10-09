from django.contrib import admin

from .models import RecommendationFeedback, RecommendationProfile

admin.site.register([RecommendationProfile, RecommendationFeedback])
