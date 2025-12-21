"""
이메일 전송 서비스
비밀번호 재설정, 아이디 찾기, 회원가입 이메일 인증
"""
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('diary')


def send_email_verification(user, token):
    """
    회원가입 이메일 인증 코드 전송
    
    Args:
        user: User 객체
        token: EmailVerificationToken 객체
    """
    subject = '[감성 일기] 이메일 인증 코드'
    
    message = f"""
안녕하세요, {user.username}님!

감성 일기에 가입해 주셔서 감사합니다.
아래 인증 코드를 입력하여 이메일 인증을 완료해주세요:

━━━━━━━━━━━━━━━━━━━━
   인증 코드: {token.token}
━━━━━━━━━━━━━━━━━━━━

⏰ 이 코드는 10분 후에 만료됩니다.

본인이 가입을 요청하지 않았다면 이 이메일을 무시해주세요.

감사합니다,
감성 일기 팀
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or 'noreply@emotionaldiary.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Email verification sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def send_password_reset_email(user, token):
    """
    비밀번호 재설정 인증 코드 이메일 전송
    
    Args:
        user: User 객체
        token: PasswordResetToken 객체
    """
    subject = '[감성 일기] 비밀번호 재설정 인증 코드'
    
    message = f"""
안녕하세요, {user.username}님!

비밀번호 재설정을 요청하셨습니다.
아래 인증 코드를 입력해주세요:

━━━━━━━━━━━━━━━━━━━━
   인증 코드: {token.token}
━━━━━━━━━━━━━━━━━━━━

⏰ 이 코드는 30분 후에 만료됩니다.

본인이 요청하지 않았다면 이 이메일을 무시해주세요.
계정은 안전하게 보호되고 있습니다.

감사합니다,
감성 일기 팀
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or 'noreply@emotionaldiary.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return False


def send_username_email(user):
    """
    아이디 찾기 이메일 전송
    
    Args:
        user: User 객체
    """
    subject = '[감성 일기] 아이디 찾기 결과'
    
    # 아이디 일부 마스킹 (예: tester123 -> te****23)
    username = user.username
    if len(username) > 4:
        masked = username[:2] + '*' * (len(username) - 4) + username[-2:]
    else:
        masked = username[0] + '*' * (len(username) - 1)
    
    message = f"""
안녕하세요!

요청하신 아이디 찾기 결과입니다.

━━━━━━━━━━━━━━━━━━━━
   가입된 아이디: {masked}
━━━━━━━━━━━━━━━━━━━━

전체 아이디: {username}

이제 이 아이디로 로그인하실 수 있습니다.
비밀번호가 기억나지 않으신다면 '비밀번호 찾기'를 이용해주세요.

감사합니다,
감성 일기 팀
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or 'noreply@emotionaldiary.com',
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Username email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send username email to {user.email}: {e}")
        return False
