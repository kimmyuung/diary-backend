# diary/views/auth_views.py
"""
인증 관련 API 뷰
- 회원가입
- 이메일 인증
- 비밀번호 재설정
- 아이디 찾기
"""
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ..serializers import UserRegisterSerializer
from config.throttling import (
    LoginRateThrottle,
    RegisterRateThrottle,
    PasswordResetRateThrottle,
    EmailResendRateThrottle,
)


class RegisterView(generics.CreateAPIView):
    """
    회원가입 API (이메일 인증 필요)
    
    POST /api/register/
    
    1. 회원가입 요청 → 계정 생성 (비활성화 상태) → 이메일로 인증코드 전송
    2. POST /api/email/verify/ 로 인증코드 확인 → 계정 활성화
    
    Request Body:
        {
            "username": "사용자명",
            "email": "이메일 (필수, 중복 불가)",
            "password": "비밀번호",
            "password_confirm": "비밀번호 확인"
        }
    
    Response (201 Created):
        {
            "message": "인증 코드가 이메일로 전송되었습니다.",
            "email": "이메일",
            "requires_verification": true
        }
    """
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]  # 시간당 5회 제한

    def create(self, request, *args, **kwargs):
        from ..models import EmailVerificationToken
        from ..email_service import send_email_verification

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 계정 비활성화 (이메일 인증 전까지)
        user.is_active = False
        user.save()
        
        # 이메일 인증 토큰 생성 및 전송
        token = EmailVerificationToken.generate_token(user)
        send_email_verification(user, token)

        return Response({
            "message": "인증 코드가 이메일로 전송되었습니다. 10분 내에 인증을 완료해주세요.",
            "email": user.email,
            "requires_verification": True
        }, status=status.HTTP_201_CREATED)


class EmailVerifyView(APIView):
    """
    이메일 인증 확인 API
    
    POST /api/email/verify/
    
    Request Body:
        {
            "email": "user@example.com",
            "code": "123456"
        }
    
    Response:
        {
            "message": "이메일 인증이 완료되었습니다. 로그인해주세요."
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]  # 분당 5회 제한 (브루트포스 방지)

    def post(self, request):
        from django.contrib.auth.models import User
        from ..models import EmailVerificationToken

        email = request.data.get('email', '').strip()
        code = request.data.get('code', '').strip()

        if not email or not code:
            return Response(
                {"error": "이메일과 인증 코드를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 요청입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 이미 활성화된 계정
        if user.is_active:
            return Response(
                {"error": "이미 인증된 계정입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 토큰 검증
        try:
            token = EmailVerificationToken.objects.get(
                user=user,
                token=code,
                is_verified=False
            )
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 인증 코드입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if token.is_expired:
            return Response(
                {"error": "인증 코드가 만료되었습니다. 다시 요청해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 인증 완료
        token.is_verified = True
        token.save()

        # 계정 활성화
        user.is_active = True
        user.save()

        return Response({
            "message": "이메일 인증이 완료되었습니다. 로그인해주세요."
        })


class ResendVerificationView(APIView):
    """
    인증 코드 재전송 API
    
    POST /api/email/resend/
    
    Request Body:
        {
            "email": "user@example.com"
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [EmailResendRateThrottle]  # 10분당 3회 제한 (이메일 남용 방지)

    def post(self, request):
        from django.contrib.auth.models import User
        from ..models import EmailVerificationToken
        from ..email_service import send_email_verification

        email = request.data.get('email', '').strip()

        if not email:
            return Response(
                {"error": "이메일을 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "message": "해당 이메일로 가입된 계정이 있다면 인증 코드가 전송됩니다."
            })

        # 이미 활성화된 계정
        if user.is_active:
            return Response(
                {"error": "이미 인증된 계정입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 새 토큰 생성 및 전송
        token = EmailVerificationToken.generate_token(user)
        send_email_verification(user, token)

        return Response({
            "message": "인증 코드가 이메일로 전송되었습니다."
        })


class PasswordResetRequestView(APIView):
    """
    비밀번호 재설정 요청 API
    이메일로 6자리 인증 코드 전송
    
    POST /api/password/reset-request/
    
    Request Body:
        {
            "email": "user@example.com"
        }
    
    Response:
        {
            "message": "인증 코드가 이메일로 전송되었습니다."
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]  # 시간당 3회 제한 (이메일 폭탄 방지)

    def post(self, request):
        from django.contrib.auth.models import User
        from ..models import PasswordResetToken
        from ..email_service import send_password_reset_email

        email = request.data.get('email', '').strip()

        if not email:
            return Response(
                {"error": "이메일을 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 보안: 이메일 존재 여부를 노출하지 않음
            return Response({
                "message": "해당 이메일로 가입된 계정이 있다면 인증 코드가 전송됩니다."
            })

        # 토큰 생성 및 이메일 전송
        token = PasswordResetToken.generate_token(user)
        email_sent = send_password_reset_email(user, token)

        if email_sent:
            return Response({
                "message": "인증 코드가 이메일로 전송되었습니다. 30분 내에 입력해주세요."
            })
        else:
            return Response(
                {"error": "이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetConfirmView(APIView):
    """
    비밀번호 재설정 확인 API
    인증 코드 검증 후 새 비밀번호 설정
    
    POST /api/password/reset-confirm/
    
    Request Body:
        {
            "email": "user@example.com",
            "code": "123456",
            "new_password": "newPassword123"
        }
    
    Response:
        {
            "message": "비밀번호가 성공적으로 변경되었습니다."
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]  # 시간당 3회 제한

    def post(self, request):
        from django.contrib.auth.models import User
        from ..models import PasswordResetToken
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        email = request.data.get('email', '').strip()
        code = request.data.get('code', '').strip()
        new_password = request.data.get('new_password', '')

        if not all([email, code, new_password]):
            return Response(
                {"error": "이메일, 인증 코드, 새 비밀번호를 모두 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 요청입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 토큰 검증
        try:
            token = PasswordResetToken.objects.get(
                user=user,
                token=code,
                is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 인증 코드입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if token.is_expired:
            return Response(
                {"error": "인증 코드가 만료되었습니다. 다시 요청해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 비밀번호 유효성 검사
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"error": list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 비밀번호 변경
        user.set_password(new_password)
        user.save()

        # 토큰 사용 처리
        token.is_used = True
        token.save()

        return Response({
            "message": "비밀번호가 성공적으로 변경되었습니다. 새 비밀번호로 로그인해주세요."
        })


class FindUsernameView(APIView):
    """
    아이디 찾기 API
    이메일로 가입된 아이디 전송
    
    POST /api/username/find/
    
    Request Body:
        {
            "email": "user@example.com"
        }
    
    Response:
        {
            "message": "아이디 정보가 이메일로 전송되었습니다."
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]  # 시간당 3회 제한

    def post(self, request):
        from django.contrib.auth.models import User
        from ..email_service import send_username_email

        email = request.data.get('email', '').strip()

        if not email:
            return Response(
                {"error": "이메일을 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 보안: 이메일 존재 여부를 노출하지 않음
            return Response({
                "message": "해당 이메일로 가입된 계정이 있다면 아이디 정보가 전송됩니다."
            })

        email_sent = send_username_email(user)

        if email_sent:
            return Response({
                "message": "아이디 정보가 이메일로 전송되었습니다."
            })
        else:
            return Response(
                {"error": "이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
