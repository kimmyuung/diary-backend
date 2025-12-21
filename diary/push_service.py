"""
푸시 알림 서비스
- Expo Push Notification API 연동
"""
import logging
import requests
from typing import List, Optional
from .models import PushToken

logger = logging.getLogger('diary')

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    sound: str = 'default',
    badge: Optional[int] = None,
) -> dict:
    """
    단일 사용자에게 푸시 알림 전송
    
    Args:
        push_token: Expo Push Token
        title: 알림 제목
        body: 알림 내용
        data: 추가 데이터 (선택)
        sound: 알림 소리 (default, null)
        badge: iOS 배지 카운트 (선택)
    
    Returns:
        Expo API 응답
    """
    message = {
        'to': push_token,
        'title': title,
        'body': body,
        'sound': sound,
    }
    
    if data:
        message['data'] = data
    
    if badge is not None:
        message['badge'] = badge
    
    try:
        response = requests.post(
            EXPO_PUSH_URL,
            json=message,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Push notification sent: {push_token[:20]}... -> {result}")
        return result
    except requests.RequestException as e:
        logger.error(f"Push notification failed: {e}")
        return {'error': str(e)}


def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> List[dict]:
    """
    특정 사용자의 모든 활성 기기에 푸시 알림 전송
    
    Args:
        user_id: 사용자 ID
        title: 알림 제목
        body: 알림 내용
        data: 추가 데이터 (선택)
    
    Returns:
        각 기기별 전송 결과 목록
    """
    tokens = PushToken.objects.filter(
        user_id=user_id,
        is_active=True
    ).values_list('token', flat=True)
    
    results = []
    for token in tokens:
        result = send_push_notification(token, title, body, data)
        results.append(result)
    
    return results


def send_bulk_push(
    user_ids: List[int],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> int:
    """
    여러 사용자에게 일괄 푸시 알림 전송
    
    Args:
        user_ids: 사용자 ID 목록
        title: 알림 제목
        body: 알림 내용
        data: 추가 데이터 (선택)
    
    Returns:
        전송된 알림 개수
    """
    tokens = list(PushToken.objects.filter(
        user_id__in=user_ids,
        is_active=True
    ).values_list('token', flat=True))
    
    if not tokens:
        return 0
    
    # Expo는 최대 100개씩 배치 전송 권장
    batch_size = 100
    sent_count = 0
    
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i + batch_size]
        messages = [
            {
                'to': token,
                'title': title,
                'body': body,
                'sound': 'default',
                'data': data or {},
            }
            for token in batch
        ]
        
        try:
            response = requests.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=30,
            )
            response.raise_for_status()
            sent_count += len(batch)
        except requests.RequestException as e:
            logger.error(f"Bulk push failed: {e}")
    
    return sent_count


# 편의 함수들
def notify_diary_reminder(user_id: int):
    """일기 리마인더 알림"""
    return send_push_to_user(
        user_id,
        title='📝 오늘의 일기',
        body='오늘 하루는 어땠나요? 감정을 기록해보세요.',
        data={'type': 'diary_reminder'},
    )


def notify_image_complete(user_id: int, diary_title: str):
    """AI 이미지 생성 완료 알림"""
    return send_push_to_user(
        user_id,
        title='🎨 AI 그림 완성',
        body=f'"{diary_title}" 일기에 AI가 그림을 그렸어요!',
        data={'type': 'image_complete'},
    )


def notify_weekly_report(user_id: int):
    """주간 리포트 알림"""
    return send_push_to_user(
        user_id,
        title='📊 주간 감정 리포트',
        body='이번 주 감정 분석 결과가 준비되었어요.',
        data={'type': 'weekly_report'},
    )
