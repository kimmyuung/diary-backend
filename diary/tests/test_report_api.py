"""
리포트 및 캘린더 API 테스트
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from diary.models import Diary


class ReportAPITestCase(TestCase):
    """감정 리포트 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
        
        # 테스트 일기 생성
        for i in range(5):
            Diary.objects.create(
                user=self.user,
                title=f'테스트 일기 {i}',
                content=f'내용 {i}',
                emotion='happy' if i % 2 == 0 else 'sad',
            )
    
    def test_get_weekly_report(self):
        """주간 리포트 조회 테스트"""
        response = self.client.get('/api/diaries/report/?period=week')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('period', response.data)
        self.assertEqual(response.data['period'], 'week')
        self.assertIn('emotion_stats', response.data)
    
    def test_get_monthly_report(self):
        """월간 리포트 조회 테스트"""
        response = self.client.get('/api/diaries/report/?period=month')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'month')
    
    def test_report_emotion_stats(self):
        """리포트 감정 통계 테스트"""
        response = self.client.get('/api/diaries/report/?period=month')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        emotion_stats = response.data.get('emotion_stats', [])
        total_count = sum(stat['count'] for stat in emotion_stats)
        self.assertEqual(total_count, 5)
    
    def test_report_requires_auth(self):
        """인증 없이 리포트 조회 테스트"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/diaries/report/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AnnualReportAPITestCase(TestCase):
    """연간 리포트 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
        
        # 테스트 일기 생성
        for i in range(10):
            Diary.objects.create(
                user=self.user,
                title=f'연간 테스트 일기 {i}',
                content=f'내용 {i}',
                emotion=['happy', 'sad', 'peaceful'][i % 3],
            )
    
    def test_get_annual_report(self):
        """연간 리포트 조회 테스트"""
        year = datetime.now().year
        response = self.client.get(f'/api/diaries/annual-report/?year={year}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('year', response.data)
        self.assertIn('total_diaries', response.data)
        self.assertIn('monthly_stats', response.data)
        self.assertIn('emotion_stats', response.data)
    
    def test_annual_report_monthly_breakdown(self):
        """연간 리포트 월별 분석 테스트"""
        year = datetime.now().year
        response = self.client.get(f'/api/diaries/annual-report/?year={year}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        monthly_stats = response.data.get('monthly_stats', [])
        self.assertEqual(len(monthly_stats), 12)  # 12개월


class CalendarAPITestCase(TestCase):
    """캘린더 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
        
        # 오늘 날짜의 일기 생성
        Diary.objects.create(
            user=self.user,
            title='오늘의 일기',
            content='오늘 일기 내용',
            emotion='happy',
        )
    
    def test_get_calendar(self):
        """캘린더 조회 테스트"""
        now = datetime.now()
        response = self.client.get(f'/api/diaries/calendar/?year={now.year}&month={now.month}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('year', response.data)
        self.assertIn('month', response.data)
        self.assertIn('days', response.data)
    
    def test_calendar_shows_diary_count(self):
        """캘린더에 일기 개수 표시 테스트"""
        now = datetime.now()
        response = self.client.get(f'/api/diaries/calendar/?year={now.year}&month={now.month}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        days = response.data.get('days', {})
        today_key = now.strftime('%Y-%m-%d')
        
        if today_key in days:
            self.assertGreaterEqual(days[today_key]['count'], 1)


class GalleryAPITestCase(TestCase):
    """갤러리 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_gallery_empty(self):
        """빈 갤러리 조회 테스트"""
        response = self.client.get('/api/diaries/gallery/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_images', response.data)
        self.assertEqual(response.data['total_images'], 0)
    
    def test_gallery_requires_auth(self):
        """인증 없이 갤러리 조회 테스트"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/diaries/gallery/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LocationsAPITestCase(TestCase):
    """위치 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
        
        # 위치 정보가 있는 일기 생성
        Diary.objects.create(
            user=self.user,
            title='위치 일기',
            content='위치 내용',
            location_name='서울 강남구',
            latitude=37.4979,
            longitude=127.0276,
        )
    
    def test_get_locations(self):
        """위치 목록 조회 테스트"""
        response = self.client.get('/api/diaries/locations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_locations', response.data)
        self.assertIn('locations', response.data)
    
    def test_locations_contain_diary_info(self):
        """위치 목록에 일기 정보 포함 테스트"""
        response = self.client.get('/api/diaries/locations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        locations = response.data.get('locations', [])
        self.assertGreaterEqual(len(locations), 1)
        
        location = locations[0]
        self.assertIn('location_name', location)
        self.assertIn('latitude', location)
        self.assertIn('longitude', location)
