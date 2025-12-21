"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from diary.views import (
    TestConnectionView, TranscribeView, TranslateAudioView, SupportedLanguagesView,
    RegisterView, PasswordResetRequestView, PasswordResetConfirmView, FindUsernameView,
    EmailVerifyView, ResendVerificationView, PushTokenView
)
from config.healthcheck import HealthCheckView, SentryTestView

# =============================================================================
# Swagger/OpenAPI 스키마 설정
# =============================================================================
schema_view = get_schema_view(
   openapi.Info(
      title="AI Emotion Diary API",
      default_version='v1',
      description="""
## 🌟 감성 일기 API

당신의 하루를 AI가 듣고, 이해하고, 그림으로 그려줍니다.

### 주요 기능
- **일기 CRUD**: 일기 작성, 수정, 삭제, 조회
- **AI 감정 분석**: GPT-4o-mini 기반 감정 분석
- **AI 이미지 생성**: DALL-E 3 기반 이미지 생성
- **음성 입력**: Whisper 기반 음성-텍스트 변환
- **감정 리포트**: 주간/월간/연간 감정 통계

### 인증
JWT(JSON Web Token) 기반 인증을 사용합니다.
1. `/api/token/`에서 토큰 발급
2. 요청 헤더에 `Authorization: Bearer {access_token}` 추가
      """,
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="contact@emotionaldiary.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ==========================================================================
    # API 문서 (Swagger/ReDoc)
    # ==========================================================================
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/docs.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
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
