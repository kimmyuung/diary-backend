from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DiaryViewSet, TagViewSet, DiaryTemplateViewSet,
    UserPreferenceView, ThemeView,
    SummarizeView, SuggestTitleView
)

router = DefaultRouter()
router.register(r'diaries', DiaryViewSet, basename='diary')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'templates', DiaryTemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),
    
    # 사용자 설정 API
    path('preferences/', UserPreferenceView.as_view(), name='user_preferences'),
    path('preferences/theme/', ThemeView.as_view(), name='user_theme'),
    
    # AI 도우미 API
    path('summarize/', SummarizeView.as_view(), name='summarize'),
    path('suggest-title/', SuggestTitleView.as_view(), name='suggest_title'),
]
