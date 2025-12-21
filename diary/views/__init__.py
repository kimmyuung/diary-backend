# diary/views/__init__.py
"""
Views 모듈
기능별로 분리된 뷰들을 export합니다.
"""

# 인증 관련 뷰
from .auth_views import (
    RegisterView,
    EmailVerifyView,
    ResendVerificationView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    FindUsernameView,
)

# 일기 관련 뷰
from .diary_views import DiaryViewSet

# 태그 관련 뷰
from .tag_views import TagViewSet

# 템플릿 관련 뷰
from .template_views import DiaryTemplateViewSet

# 사용자 설정 관련 뷰
from .preference_views import UserPreferenceView, ThemeView

# AI 관련 뷰
from .ai_views import SummarizeView, SuggestTitleView

# 음성 인식 관련 뷰
from .speech_views import (
    TranscribeView,
    TranslateAudioView,
    SupportedLanguagesView,
)

# 푸시 알림 관련 뷰
from .push_views import PushTokenView

# 공통/유틸리티 뷰
from .common_views import TestConnectionView


__all__ = [
    # Auth
    'RegisterView',
    'EmailVerifyView',
    'ResendVerificationView',
    'PasswordResetRequestView',
    'PasswordResetConfirmView',
    'FindUsernameView',
    # Diary
    'DiaryViewSet',
    # Tags
    'TagViewSet',
    # Templates
    'DiaryTemplateViewSet',
    # Preferences
    'UserPreferenceView',
    'ThemeView',
    # AI
    'SummarizeView',
    'SuggestTitleView',
    # Speech
    'TranscribeView',
    'TranslateAudioView',
    'SupportedLanguagesView',
    # Push
    'PushTokenView',
    # Common
    'TestConnectionView',
]
