"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from diary.views import (
    TestConnectionView, TranscribeView, TranslateAudioView, SupportedLanguagesView,
    RegisterView, PasswordResetRequestView, PasswordResetConfirmView, FindUsernameView,
    EmailVerifyView, ResendVerificationView, PushTokenView
)
from config.healthcheck import HealthCheckView, SentryTestView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 헬스체크 (모니터링용)
    path('api/health/', HealthCheckView.as_view(), name='health_check'),
    path('api/sentry-test/', SentryTestView.as_view(), name='sentry_test'),
    
    # 인증 (회원가입 + 이메일 인증)
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/email/verify/', EmailVerifyView.as_view(), name='email_verify'),
    path('api/email/resend/', ResendVerificationView.as_view(), name='email_resend'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 비밀번호/아이디 찾기
    path('api/password/reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/password/reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/username/find/', FindUsernameView.as_view(), name='find_username'),
    
    # 테스트 엔드포인트
    path('api/test/connection/', TestConnectionView.as_view(), name='test_connection'),
    
    # 음성-텍스트 변환 API (Whisper) - 100개 이상 언어 지원
    path('api/transcribe/', TranscribeView.as_view(), name='transcribe'),
    path('api/translate-audio/', TranslateAudioView.as_view(), name='translate_audio'),
    path('api/supported-languages/', SupportedLanguagesView.as_view(), name='supported_languages'),
    
    # 푸시 알림 토큰 관리
    path('api/push-token/', PushTokenView.as_view(), name='push_token'),
    
    # 일기 API
    path('api/', include('diary.urls')),
]

