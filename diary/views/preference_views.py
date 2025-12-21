# diary/views/preference_views.py
"""
사용자 설정 관련 API 뷰
- 테마 설정 (다크/라이트 모드)
- 알림 설정
- 기타 개인화 설정
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..models import UserPreference
from ..serializers import UserPreferenceSerializer


class UserPreferenceView(APIView):
    """
    사용자 설정 API
    
    GET: 현재 설정 조회
    PUT/PATCH: 설정 업데이트
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        현재 사용자의 설정 조회
        
        GET /api/preferences/
        
        Response:
            {
                "theme": "dark",
                "language": "ko",
                "push_enabled": true,
                "daily_reminder_enabled": false,
                "daily_reminder_time": null,
                "auto_emotion_analysis": true,
                "show_location": true,
                "updated_at": "2024-12-22T..."
            }
        """
        preference = UserPreference.get_or_create_for_user(request.user)
        serializer = UserPreferenceSerializer(preference)
        return Response(serializer.data)
    
    def put(self, request):
        """
        사용자 설정 전체 업데이트
        
        PUT /api/preferences/
        """
        preference = UserPreference.get_or_create_for_user(request.user)
        serializer = UserPreferenceSerializer(preference, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """
        사용자 설정 부분 업데이트
        
        PATCH /api/preferences/
        
        Request Body (예시):
            {
                "theme": "dark"
            }
        """
        preference = UserPreference.get_or_create_for_user(request.user)
        serializer = UserPreferenceSerializer(
            preference, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ThemeView(APIView):
    """
    테마 설정 전용 API (간편 접근용)
    
    GET: 현재 테마 조회
    PUT: 테마 변경
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        현재 테마 조회
        
        GET /api/preferences/theme/
        
        Response:
            {
                "theme": "dark",
                "theme_display": "다크 모드"
            }
        """
        preference = UserPreference.get_or_create_for_user(request.user)
        theme_display = dict(UserPreference.THEME_CHOICES).get(preference.theme, preference.theme)
        
        return Response({
            'theme': preference.theme,
            'theme_display': theme_display
        })
    
    def put(self, request):
        """
        테마 변경
        
        PUT /api/preferences/theme/
        
        Request Body:
            {
                "theme": "dark"  // "light", "dark", "system"
            }
        """
        theme = request.data.get('theme')
        
        valid_themes = [choice[0] for choice in UserPreference.THEME_CHOICES]
        if theme not in valid_themes:
            return Response(
                {'error': f'유효하지 않은 테마입니다. 가능한 값: {", ".join(valid_themes)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        preference = UserPreference.get_or_create_for_user(request.user)
        preference.theme = theme
        preference.save()
        
        theme_display = dict(UserPreference.THEME_CHOICES).get(theme, theme)
        
        return Response({
            'theme': preference.theme,
            'theme_display': theme_display,
            'message': f'{theme_display}로 변경되었습니다.'
        })
