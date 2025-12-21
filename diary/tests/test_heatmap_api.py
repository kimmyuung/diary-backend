# diary/tests/test_heatmap_api.py
"""
감정 히트맵 API 테스트
"""
import pytest
from datetime import datetime, timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone
from diary.models import Diary


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
class TestHeatmapAPI:
    """감정 히트맵 API 테스트"""

    def test_get_heatmap_empty(self, authenticated_client):
        """일기 없는 경우 히트맵 테스트"""
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['year'] == year
        assert response.data['total_entries'] == 0
        assert response.data['streak']['current'] == 0
        assert response.data['streak']['longest'] == 0

    def test_get_heatmap_with_diaries(self, authenticated_client):
        """일기 있는 경우 히트맵 테스트"""
        # 오늘 일기 생성
        Diary.objects.create(
            user=authenticated_client.user,
            title='오늘 일기',
            content='내용',
            emotion='happy'
        )
        
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_entries'] == 1
        
        # 오늘 날짜에 데이터가 있어야 함
        today = timezone.now().strftime('%Y-%m-%d')
        assert response.data['data'][today] is not None
        assert response.data['data'][today]['count'] == 1
        assert response.data['data'][today]['emotion'] == 'happy'

    def test_emotion_colors_mapping(self, authenticated_client):
        """감정별 색상 매핑 테스트"""
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'emotion_colors' in response.data
        assert response.data['emotion_colors']['happy'] == '#FFD93D'
        assert response.data['emotion_colors']['sad'] == '#6B7FD7'
        assert response.data['emotion_colors']['angry'] == '#FF6B6B'

    def test_monthly_summary(self, authenticated_client):
        """월별 요약 테스트"""
        # 1월에 일기 3개 생성
        for i in range(3):
            diary = Diary.objects.create(
                user=authenticated_client.user,
                title=f'일기{i}',
                content=f'내용{i}',
                emotion='happy'
            )
        
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['monthly_summary']) == 12  # 12개월
        
        # 현재 월의 count 확인
        current_month = timezone.now().month
        month_data = next(
            m for m in response.data['monthly_summary'] 
            if m['month'] == current_month
        )
        assert month_data['count'] == 3

    def test_different_year(self, authenticated_client):
        """다른 연도 조회 테스트"""
        response = authenticated_client.get('/api/diaries/heatmap/?year=2020')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['year'] == 2020
        assert response.data['total_entries'] == 0

    def test_invalid_year(self, authenticated_client):
        """잘못된 연도 테스트"""
        response = authenticated_client.get('/api/diaries/heatmap/?year=invalid')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_all_days_in_year(self, authenticated_client):
        """1년 전체 날짜 포함 테스트"""
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.status_code == status.HTTP_200_OK
        
        # 365일 또는 366일 (윤년) 데이터가 있어야 함
        data_count = len(response.data['data'])
        assert data_count >= 365
        assert data_count <= 366


@pytest.mark.django_db
class TestStreakCalculation:
    """연속 작성일 계산 테스트"""

    def test_current_streak_today(self, authenticated_client):
        """오늘 작성 시 현재 연속 1일"""
        Diary.objects.create(
            user=authenticated_client.user,
            title='오늘',
            content='내용'
        )
        
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.data['streak']['current'] >= 1

    def test_no_streak_no_entries(self, authenticated_client):
        """일기 없으면 연속 0일"""
        year = timezone.now().year
        response = authenticated_client.get(f'/api/diaries/heatmap/?year={year}')
        
        assert response.data['streak']['current'] == 0
        assert response.data['streak']['longest'] == 0
