"""
헬스체크 및 모니터링 엔드포인트
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection
import os


class HealthCheckView(APIView):
    """
    서비스 상태 확인 엔드포인트
    
    GET /api/health/
    
    Response:
        {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # 데이터베이스 연결 확인
        db_status = "connected"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            db_status = "disconnected"
        
        return Response({
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "database": db_status,
            "version": os.environ.get('SENTRY_RELEASE', '1.0.0'),
            "environment": os.environ.get('SENTRY_ENVIRONMENT', 'development'),
        })


class SentryTestView(APIView):
    """
    Sentry 연동 테스트용 엔드포인트 (개발/테스트용)
    
    GET /api/sentry-test/
    
    주의: 이 엔드포인트는 의도적으로 에러를 발생시킵니다.
    Sentry 대시보드에서 에러가 수신되는지 확인하는 용도입니다.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # 의도적인 에러 발생 (Sentry 테스트용)
        try:
            division_by_zero = 1 / 0
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
            return Response({
                "status": "error_captured",
                "message": "테스트 에러가 Sentry로 전송되었습니다. Sentry 대시보드를 확인하세요."
            })
