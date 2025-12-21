# config/throttling.py
"""
Rate Limiting (속도 제한) 설정

보안 강화를 위해 민감한 API 엔드포인트에 대한 요청 횟수를 제한합니다.
브루트포스 공격, DDoS, 스팸 등을 방지합니다.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    로그인 시도 제한
    - 비로그인 사용자 (IP 기반)
    - 분당 5회로 제한
    - 브루트포스 공격 방지
    """
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """
    회원가입 제한
    - 비로그인 사용자 (IP 기반)  
    - 시간당 5회로 제한
    - 스팸 계정 생성 방지
    """
    scope = 'register'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    비밀번호 재설정 제한
    - 비로그인 사용자 (IP 기반)
    - 시간당 3회로 제한
    - 이메일 폭탄 방지
    """
    scope = 'password_reset'


class EmailResendRateThrottle(AnonRateThrottle):
    """
    이메일 재전송 제한
    - 비로그인 사용자 (IP 기반)
    - 10분당 3회로 제한
    - 이메일 남용 방지
    """
    scope = 'email_resend'


class AIImageGenerationThrottle(UserRateThrottle):
    """
    AI 이미지 생성 제한
    - 로그인 사용자 (User ID 기반)
    - 일당 20회로 제한
    - API 비용 관리
    """
    scope = 'ai_image'


class TranscriptionRateThrottle(UserRateThrottle):
    """
    음성 인식(STT) 제한
    - 로그인 사용자 (User ID 기반)
    - 시간당 30회로 제한
    - API 비용 관리
    """
    scope = 'transcription'


class BurstRateThrottle(AnonRateThrottle):
    """
    일반적인 버스트 제한
    - 비로그인 사용자
    - 초당 10회로 제한
    - DDoS 기본 방어
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    지속적인 사용 제한
    - 로그인 사용자
    - 일당 10000회로 제한
    - 정상 사용 보장 + 남용 방지
    """
    scope = 'sustained'
