"""
푸시 알림 API 및 서비스 테스트
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from diary.models import PushToken


class PushTokenViewTestCase(TestCase):
    """푸시 토큰 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        self.push_token_url = '/api/push-token/'
        
        # 테스트 사용자 생성 및 인증
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_register_push_token_success(self):
        """푸시 토큰 등록 성공 테스트"""
        data = {
            'token': 'ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]',
            'device_type': 'android',
            'device_name': 'Test Device',
        }
        
        response = self.client.post(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token_id', response.data)
        
        # 토큰이 저장되었는지 확인
        self.assertTrue(PushToken.objects.filter(token=data['token']).exists())
    
    def test_register_push_token_update_existing(self):
        """기존 푸시 토큰 업데이트 테스트"""
        token_value = 'ExponentPushToken[existing]'
        
        # 기존 토큰 생성
        PushToken.objects.create(
            user=self.user,
            token=token_value,
            device_type='ios',
        )
        
        # 같은 토큰으로 다시 등록 (업데이트)
        data = {
            'token': token_value,
            'device_type': 'android',  # 변경
        }
        
        response = self.client.post(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 업데이트되었는지 확인
        updated_token = PushToken.objects.get(token=token_value)
        self.assertEqual(updated_token.device_type, 'android')
    
    def test_register_push_token_missing_token(self):
        """푸시 토큰 없이 등록 시도 테스트"""
        data = {
            'device_type': 'android',
        }
        
        response = self.client.post(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_deactivate_push_token_success(self):
        """푸시 토큰 비활성화 성공 테스트"""
        token_value = 'ExponentPushToken[todeactivate]'
        
        PushToken.objects.create(
            user=self.user,
            token=token_value,
            device_type='android',
            is_active=True,
        )
        
        data = {'token': token_value}
        
        response = self.client.delete(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 비활성화되었는지 확인
        deactivated_token = PushToken.objects.get(token=token_value)
        self.assertFalse(deactivated_token.is_active)
    
    def test_deactivate_nonexistent_token(self):
        """존재하지 않는 토큰 비활성화 테스트"""
        data = {'token': 'ExponentPushToken[nonexistent]'}
        
        response = self.client.delete(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_push_token_requires_auth(self):
        """인증 없이 푸시 토큰 등록 시도 테스트"""
        self.client.force_authenticate(user=None)  # 인증 해제
        
        data = {
            'token': 'ExponentPushToken[test]',
            'device_type': 'android',
        }
        
        response = self.client.post(self.push_token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PushServiceTestCase(TestCase):
    """푸시 알림 서비스 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        # 푸시 토큰 생성
        self.push_token = PushToken.objects.create(
            user=self.user,
            token='ExponentPushToken[testtoken]',
            device_type='android',
            is_active=True,
        )
    
    @patch('diary.push_service.requests.post')
    def test_send_push_notification_success(self, mock_post):
        """푸시 알림 전송 성공 테스트"""
        from diary.push_service import send_push_notification
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'status': 'ok'}}
        mock_post.return_value = mock_response
        
        result = send_push_notification(
            push_token=self.push_token.token,
            title='테스트 알림',
            body='알림 내용입니다.',
        )
        
        mock_post.assert_called_once()
        self.assertIn('data', result)
    
    @patch('diary.push_service.requests.post')
    def test_send_push_to_user(self, mock_post):
        """사용자에게 푸시 알림 전송 테스트"""
        from diary.push_service import send_push_to_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'status': 'ok'}}
        mock_post.return_value = mock_response
        
        results = send_push_to_user(
            user_id=self.user.id,
            title='테스트',
            body='내용',
        )
        
        self.assertEqual(len(results), 1)
    
    @patch('diary.push_service.requests.post')
    def test_notify_diary_reminder(self, mock_post):
        """일기 리마인더 알림 테스트"""
        from diary.push_service import notify_diary_reminder
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'status': 'ok'}}
        mock_post.return_value = mock_response
        
        results = notify_diary_reminder(self.user.id)
        
        self.assertEqual(len(results), 1)
        
        # 호출 인자 확인
        call_args = mock_post.call_args
        sent_data = call_args[1]['json']
        self.assertEqual(sent_data['title'], '📝 오늘의 일기')


class PushTokenModelTestCase(TestCase):
    """PushToken 모델 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_create_push_token(self):
        """푸시 토큰 생성 테스트"""
        token = PushToken.objects.create(
            user=self.user,
            token='ExponentPushToken[test123]',
            device_type='ios',
        )
        
        self.assertIsNotNone(token.id)
        self.assertEqual(token.user, self.user)
        self.assertTrue(token.is_active)
    
    def test_push_token_str(self):
        """푸시 토큰 문자열 표현 테스트"""
        token = PushToken.objects.create(
            user=self.user,
            token='ExponentPushToken[test123]',
            device_type='android',
        )
        
        self.assertIn('testuser', str(token))
        self.assertIn('android', str(token))
    
    def test_push_token_unique(self):
        """푸시 토큰 유일성 테스트"""
        token_value = 'ExponentPushToken[unique]'
        
        PushToken.objects.create(
            user=self.user,
            token=token_value,
            device_type='android',
        )
        
        # 같은 토큰으로 다시 생성 시도
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PushToken.objects.create(
                user=self.user,
                token=token_value,
                device_type='ios',
            )
