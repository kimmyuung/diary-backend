"""
전역 예외 핸들러

REST Framework의 기본 예외 처리를 확장하여 일관된 에러 응답 형식을 제공합니다.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    Throttled,
)
import logging

logger = logging.getLogger('diary')


# 에러 코드 정의
class ErrorCodes:
    # 인증 관련
    AUTH_REQUIRED = 'AUTH_REQUIRED'
    AUTH_FAILED = 'AUTH_FAILED'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    
    # 요청 관련
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    NOT_FOUND = 'NOT_FOUND'
    BAD_REQUEST = 'BAD_REQUEST'
    
    # 서버 관련
    SERVER_ERROR = 'SERVER_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
    
    # 비즈니스 로직 관련
    DIARY_NOT_FOUND = 'DIARY_NOT_FOUND'
    ENCRYPTION_ERROR = 'ENCRYPTION_ERROR'
    AI_SERVICE_ERROR = 'AI_SERVICE_ERROR'
    EMAIL_SEND_ERROR = 'EMAIL_SEND_ERROR'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'


def custom_exception_handler(exc, context):
    """
    커스텀 예외 핸들러
    
    - 모든 예외를 일관된 형식으로 반환
    - 로깅 추가
    - Sentry 연동 (이미 설정됨)
    """
    # 먼저 기본 핸들러 호출
    response = exception_handler(exc, context)
    
    # 요청 정보 추출
    request = context.get('request')
    view = context.get('view')
    view_name = view.__class__.__name__ if view else 'Unknown'
    
    # 로깅용 메타 정보
    meta = {
        'view': view_name,
        'method': request.method if request else 'Unknown',
        'path': request.path if request else 'Unknown',
        'user': str(request.user) if request and hasattr(request, 'user') else 'Anonymous',
    }
    
    # DRF가 처리하지 못한 예외
    if response is None:
        # Django ValidationError 처리
        if isinstance(exc, DjangoValidationError):
            logger.warning(f"Validation error: {exc} | {meta}")
            return Response(
                {
                    'success': False,
                    'error': '입력값이 올바르지 않습니다',
                    'code': ErrorCodes.VALIDATION_ERROR,
                    'details': exc.messages if hasattr(exc, 'messages') else str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기타 예외 (500 에러)
        logger.error(f"Unhandled exception: {type(exc).__name__}: {exc} | {meta}")
        return Response(
            {
                'success': False,
                'error': '서버 오류가 발생했습니다',
                'code': ErrorCodes.SERVER_ERROR,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # DRF 예외 타입별 처리
    error_mapping = {
        NotAuthenticated: (ErrorCodes.AUTH_REQUIRED, '로그인이 필요합니다'),
        AuthenticationFailed: (ErrorCodes.AUTH_FAILED, '인증에 실패했습니다'),
        PermissionDenied: (ErrorCodes.PERMISSION_DENIED, '접근 권한이 없습니다'),
        NotFound: (ErrorCodes.NOT_FOUND, '요청한 리소스를 찾을 수 없습니다'),
        Throttled: (ErrorCodes.RATE_LIMIT_EXCEEDED, '요청이 너무 많습니다. 잠시 후 다시 시도해주세요'),
    }
    
    for exc_class, (code, message) in error_mapping.items():
        if isinstance(exc, exc_class):
            response.data = {
                'success': False,
                'error': message,
                'code': code,
            }
            # Throttled의 경우 대기 시간 추가
            if isinstance(exc, Throttled):
                response.data['retry_after'] = exc.wait
            
            logger.info(f"{code}: {message} | {meta}")
            return response
    
    # ValidationError 처리
    if isinstance(exc, ValidationError):
        logger.warning(f"Validation error: {exc.detail} | {meta}")
        response.data = {
            'success': False,
            'error': '입력값이 올바르지 않습니다',
            'code': ErrorCodes.VALIDATION_ERROR,
            'details': exc.detail,
        }
        return response
    
    # 기타 API 예외
    if isinstance(exc, APIException):
        logger.warning(f"API exception: {exc.detail} | {meta}")
        response.data = {
            'success': False,
            'error': str(exc.detail) if hasattr(exc, 'detail') else '오류가 발생했습니다',
            'code': getattr(exc, 'default_code', ErrorCodes.BAD_REQUEST),
        }
        return response
    
    return response


class APIErrorMixin:
    """
    뷰에서 사용할 수 있는 에러 응답 헬퍼 믹스인
    """
    
    def error_response(self, message, code=ErrorCodes.BAD_REQUEST, 
                       details=None, status_code=status.HTTP_400_BAD_REQUEST):
        """일관된 에러 응답 생성"""
        data = {
            'success': False,
            'error': message,
            'code': code,
        }
        if details:
            data['details'] = details
        return Response(data, status=status_code)
    
    def success_response(self, data=None, message=None, 
                         status_code=status.HTTP_200_OK):
        """일관된 성공 응답 생성"""
        response_data = {'success': True}
        if message:
            response_data['message'] = message
        if data is not None:
            response_data['data'] = data
        return Response(response_data, status=status_code)
