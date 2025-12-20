"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from diary.views import TestConnectionView, TranscribeView, TranslateAudioView, SupportedLanguagesView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT 인증
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 테스트 엔드포인트
    path('api/test/connection/', TestConnectionView.as_view(), name='test_connection'),
    
    # 음성-텍스트 변환 API (Whisper) - 100개 이상 언어 지원
    path('api/transcribe/', TranscribeView.as_view(), name='transcribe'),
    path('api/translate-audio/', TranslateAudioView.as_view(), name='translate_audio'),
    path('api/supported-languages/', SupportedLanguagesView.as_view(), name='supported_languages'),
    
    # 일기 API
    path('api/', include('diary.urls')),
]

