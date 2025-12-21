# diary/tests/test_preference_api.py
"""
사용자 설정 API 테스트
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from diary.models import UserPreference


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.mark.django_db
class TestUserPreferenceAPI:
    """사용자 설정 API 테스트"""

    def test_get_preferences_creates_default(self, authenticated_client):
        """설정 조회 시 기본값 자동 생성 테스트"""
        # 처음에는 설정이 없음
        assert not UserPreference.objects.filter(user=authenticated_client.user).exists()
        
        response = authenticated_client.get('/api/preferences/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'system'  # 기본값
        assert response.data['language'] == 'ko'   # 기본값
        
        # 이제 설정이 생성됨
        assert UserPreference.objects.filter(user=authenticated_client.user).exists()

    def test_update_theme(self, authenticated_client):
        """테마 변경 테스트"""
        response = authenticated_client.patch('/api/preferences/', {
            'theme': 'dark'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'dark'
        
        # DB 확인
        pref = UserPreference.objects.get(user=authenticated_client.user)
        assert pref.theme == 'dark'

    def test_update_multiple_settings(self, authenticated_client):
        """여러 설정 동시 변경 테스트"""
        response = authenticated_client.patch('/api/preferences/', {
            'theme': 'light',
            'language': 'en',
            'push_enabled': False,
            'auto_emotion_analysis': False 
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'light'
        assert response.data['language'] == 'en'
        assert response.data['push_enabled'] is False
        assert response.data['auto_emotion_analysis'] is False

    def test_invalid_theme_value(self, authenticated_client):
        """잘못된 테마 값 테스트"""
        response = authenticated_client.patch('/api/preferences/', {
            'theme': 'invalid_theme'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestThemeAPI:
    """테마 전용 API 테스트"""

    def test_get_theme(self, authenticated_client):
        """테마 조회 테스트"""
        response = authenticated_client.get('/api/preferences/theme/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'theme' in response.data
        assert 'theme_display' in response.data

    def test_set_theme_dark(self, authenticated_client):
        """다크 모드 설정 테스트"""
        response = authenticated_client.put('/api/preferences/theme/', {
            'theme': 'dark'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'dark'
        assert '다크' in response.data['theme_display']

    def test_set_theme_light(self, authenticated_client):
        """라이트 모드 설정 테스트"""
        response = authenticated_client.put('/api/preferences/theme/', {
            'theme': 'light'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'light'
        assert '라이트' in response.data['theme_display']

    def test_set_theme_system(self, authenticated_client):
        """시스템 설정 따르기 테스트"""
        response = authenticated_client.put('/api/preferences/theme/', {
            'theme': 'system'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['theme'] == 'system'
        assert '시스템' in response.data['theme_display']

    def test_invalid_theme(self, authenticated_client):
        """잘못된 테마 값 거부 테스트"""
        response = authenticated_client.put('/api/preferences/theme/', {
            'theme': 'purple'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data


@pytest.mark.django_db
class TestPreferenceIsolation:
    """사용자 간 설정 격리 테스트"""

    def test_settings_not_shared(self, api_client):
        """다른 사용자의 설정이 공유되지 않음"""
        user1 = User.objects.create_user('user1', 'user1@test.com', 'pass123')
        user2 = User.objects.create_user('user2', 'user2@test.com', 'pass123')
        
        # User1 설정
        api_client.force_authenticate(user=user1)
        api_client.patch('/api/preferences/', {'theme': 'dark'})
        
        # User2 설정 확인
        api_client.force_authenticate(user=user2)
        response = api_client.get('/api/preferences/')
        
        # User2는 기본값을 가짐
        assert response.data['theme'] == 'system'
