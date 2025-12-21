# backend/diary/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import generics
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Diary, DiaryImage
from .serializers import DiarySerializer, DiaryImageSerializer, UserRegisterSerializer
from .ai_service import ImageGenerator, SpeechToText


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

    def create(self, request, *args, **kwargs):
        from .models import EmailVerificationToken
        from .email_service import send_email_verification

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

    def post(self, request):
        from django.contrib.auth.models import User
        from .models import EmailVerificationToken

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

    def post(self, request):
        from django.contrib.auth.models import User
        from .models import EmailVerificationToken
        from .email_service import send_email_verification

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

    def post(self, request):
        from django.contrib.auth.models import User
        from .models import PasswordResetToken
        from .email_service import send_password_reset_email

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

    def post(self, request):
        from django.contrib.auth.models import User
        from .models import PasswordResetToken
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

    def post(self, request):
        from django.contrib.auth.models import User
        from .email_service import send_username_email

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


class TestConnectionView(APIView):
    """
    React Native 앱의 연결을 테스트하기 위한 API 뷰입니다.
    """
    def get(self, request):
        return Response({
            "status": "success",
            "message": "Django 백엔드 연결 성공! React Native 앱이 API를 잘 호출했습니다.",
        })


class DiaryViewSet(viewsets.ModelViewSet):
    """
    일기(Diary) 항목에 대한 CRUD 및 AI 기능을 제공하는 ViewSet.
    
    검색 파라미터:
        - search: 제목 또는 내용 검색 (키워드)
        - emotion: 감정 필터 (happy, sad, angry 등)
        - start_date: 시작 날짜 (YYYY-MM-DD)
        - end_date: 종료 날짜 (YYYY-MM-DD)
    """
    serializer_class = DiarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        요청한 사용자에 속한 일기 항목만 반환합니다.
        검색/필터 기능 포함.
        
        검색 파라미터:
            - search: 제목 검색 (DB 레벨)
            - content_search: 본문 검색 (복호화 후 Python 레벨)
            - emotion: 감정 필터
            - start_date, end_date: 날짜 범위
        """
        queryset = Diary.objects.filter(user=self.request.user)
        
        # 키워드 검색 (제목) - DB 레벨
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
            )
        
        # 감정 필터
        emotion = self.request.query_params.get('emotion', None)
        if emotion:
            queryset = queryset.filter(emotion=emotion)
        
        # 날짜 범위 필터
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=start.date())
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=end.date())
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """
        일기 목록 조회 - 본문 검색 포함
        
        본문 검색은 암호화되어 있어 DB에서 직접 검색 불가.
        queryset을 가져온 후 Python에서 복호화하여 필터링.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # 본문 검색 (암호화된 내용을 복호화 후 검색)
        content_search = request.query_params.get('content_search', None)
        if content_search:
            search_lower = content_search.lower()
            filtered_ids = []
            for diary in queryset:
                try:
                    decrypted = diary.decrypt_content()
                    if decrypted and search_lower in decrypted.lower():
                        filtered_ids.append(diary.id)
                except Exception:
                    pass
            queryset = queryset.filter(id__in=filtered_ids)
        
        # 통합 검색 (제목 + 본문) - 'q' 파라미터
        q = request.query_params.get('q', None)
        if q:
            q_lower = q.lower()
            title_matched_ids = list(
                queryset.filter(title__icontains=q).values_list('id', flat=True)
            )
            content_matched_ids = []
            for diary in queryset.exclude(id__in=title_matched_ids):
                try:
                    decrypted = diary.decrypt_content()
                    if decrypted and q_lower in decrypted.lower():
                        content_matched_ids.append(diary.id)
                except Exception:
                    pass
            all_matched_ids = title_matched_ids + content_matched_ids
            queryset = Diary.objects.filter(id__in=all_matched_ids).order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        새로운 일기 항목을 생성할 때 현재 사용자를 자동으로 할당합니다.
        """
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='report')
    def report(self, request):
        """
        사용자의 감정 리포트를 반환합니다.
        
        Query Parameters:
            - period: 'week' (기본값) 또는 'month'
        
        Response:
            {
                "period": "week",
                "total_diaries": 5,
                "data_sufficient": true,
                "recommended_count": 7,
                "emotion_stats": [
                    {"emotion": "happy", "label": "행복", "count": 3, "percentage": 60},
                    ...
                ],
                "dominant_emotion": {"emotion": "happy", "label": "행복"},
                "insight": "이번 주 가장 많이 느낀 감정은 행복이에요."
            }
        """
        period = request.query_params.get('period', 'week')
        
        # 기간 설정
        now = timezone.now()
        if period == 'month':
            start_date = now - timedelta(days=30)
            period_label = '한 달'
            recommended_count = 15
        else:
            start_date = now - timedelta(days=7)
            period_label = '일주일'
            recommended_count = 7
        
        # 해당 기간 일기 조회
        diaries = Diary.objects.filter(
            user=request.user,
            created_at__gte=start_date,
            emotion__isnull=False
        )
        
        total_count = diaries.count()
        data_sufficient = total_count >= recommended_count
        
        # 감정별 통계
        emotion_counts = diaries.values('emotion').annotate(
            count=Count('emotion')
        ).order_by('-count')
        
        emotion_labels = {
            'happy': '행복',
            'sad': '슬픔',
            'angry': '화남',
            'anxious': '불안',
            'peaceful': '평온',
            'excited': '신남',
            'tired': '피곤',
            'love': '사랑',
        }
        
        emotion_stats = []
        for item in emotion_counts:
            emotion = item['emotion']
            count = item['count']
            percentage = round((count / total_count) * 100) if total_count > 0 else 0
            emotion_stats.append({
                'emotion': emotion,
                'label': emotion_labels.get(emotion, emotion),
                'count': count,
                'percentage': percentage,
            })
        
        # 가장 많은 감정
        dominant_emotion = None
        insight = None
        if emotion_stats:
            top = emotion_stats[0]
            dominant_emotion = {
                'emotion': top['emotion'],
                'label': top['label'],
            }
            insight = f"이번 {period_label} 가장 많이 느낀 감정은 {top['label']}이에요."
        else:
            insight = f"이번 {period_label} 기록된 감정이 없어요. 일기를 작성해보세요!"
        
        return Response({
            'period': period,
            'period_label': period_label,
            'total_diaries': total_count,
            'data_sufficient': data_sufficient,
            'recommended_count': recommended_count,
            'emotion_stats': emotion_stats,
            'dominant_emotion': dominant_emotion,
            'insight': insight,
        })

    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        """
        캘린더 뷰를 위한 월별 일기 요약을 반환합니다.
        본인의 일기만 조회됩니다.
        
        Query Parameters:
            - year: 연도 (기본값: 현재 연도)
            - month: 월 (기본값: 현재 월)
        
        Response:
            {
                "year": 2024,
                "month": 12,
                "days": {
                    "2024-12-01": {"count": 1, "emotion": "happy", "emoji": "😊"},
                    "2024-12-05": {"count": 2, "emotion": "sad", "emoji": "😢"},
                    ...
                }
            }
        """
        now = timezone.now()
        year = request.query_params.get('year', now.year)
        month = request.query_params.get('month', now.month)
        
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response(
                {"error": "유효하지 않은 연도/월입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 월의 일기 조회 (본인 것만!)
        diaries = Diary.objects.filter(
            user=request.user,
            created_at__year=year,
            created_at__month=month
        ).order_by('created_at')
        
        # 날짜별 요약 생성
        days = {}
        for diary in diaries:
            date_str = diary.created_at.strftime('%Y-%m-%d')
            if date_str not in days:
                days[date_str] = {
                    'count': 0,
                    'emotion': diary.emotion,
                    'emoji': diary.get_emotion_display_emoji() if diary.emotion else '',
                    'diary_ids': []
                }
            days[date_str]['count'] += 1
            days[date_str]['diary_ids'].append(diary.id)
            # 여러 일기가 있으면 마지막 일기의 감정 사용
            if diary.emotion:
                days[date_str]['emotion'] = diary.emotion
                days[date_str]['emoji'] = diary.get_emotion_display_emoji()
        
        return Response({
            'year': year,
            'month': month,
            'days': days
        })

    @action(detail=False, methods=['get'], url_path='annual-report')
    def annual_report(self, request):
        """
        연간 감정 리포트를 반환합니다.
        
        Query Parameters:
            - year: 연도 (기본값: 현재 연도)
        """
        now = timezone.now()
        year = request.query_params.get('year', now.year)
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {"error": "유효하지 않은 연도입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 연도의 일기 조회
        diaries = Diary.objects.filter(
            user=request.user,
            created_at__year=year
        )
        
        total_count = diaries.count()
        
        # 월별 통계
        monthly_stats = []
        for month in range(1, 13):
            month_diaries = diaries.filter(created_at__month=month)
            month_count = month_diaries.count()
            
            # 해당 월의 주요 감정
            dominant_emotion = None
            if month_count > 0:
                emotion_counts = month_diaries.filter(emotion__isnull=False).values('emotion').annotate(
                    count=Count('emotion')
                ).order_by('-count').first()
                if emotion_counts:
                    dominant_emotion = emotion_counts['emotion']
            
            monthly_stats.append({
                'month': month,
                'count': month_count,
                'dominant_emotion': dominant_emotion
            })
        
        # 연간 감정 통계
        emotion_labels = {
            'happy': '행복', 'sad': '슬픔', 'angry': '화남', 'anxious': '불안',
            'peaceful': '평온', 'excited': '신남', 'tired': '피곤', 'love': '사랑',
        }
        
        annual_emotions = diaries.filter(emotion__isnull=False).values('emotion').annotate(
            count=Count('emotion')
        ).order_by('-count')
        
        emotion_stats = []
        for item in annual_emotions:
            emotion = item['emotion']
            count = item['count']
            percentage = round((count / total_count) * 100) if total_count > 0 else 0
            emotion_stats.append({
                'emotion': emotion,
                'label': emotion_labels.get(emotion, emotion),
                'count': count,
                'percentage': percentage,
            })
        
        return Response({
            'year': year,
            'total_diaries': total_count,
            'monthly_stats': monthly_stats,
            'emotion_stats': emotion_stats,
        })

    @action(detail=False, methods=['get'], url_path='gallery')
    def gallery(self, request):
        """
        사용자의 모든 AI 생성 이미지를 반환합니다.
        """
        images = DiaryImage.objects.filter(
            diary__user=request.user
        ).select_related('diary').order_by('-created_at')
        
        result = []
        for img in images:
            result.append({
                'id': img.id,
                'image_url': img.image_url,
                'ai_prompt': img.ai_prompt,
                'created_at': img.created_at.isoformat(),
                'diary_id': img.diary.id,
                'diary_title': img.diary.title,
                'diary_date': img.diary.created_at.strftime('%Y-%m-%d'),
            })
        
        return Response({
            'total_images': len(result),
            'images': result
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export_diaries(self, request):
        """
        사용자의 모든 일기를 JSON 형식으로 내보냅니다.
        """
        diaries = Diary.objects.filter(user=request.user).order_by('created_at')
        
        result = []
        for diary in diaries:
            result.append({
                'id': diary.id,
                'title': diary.title,
                'content': diary.decrypt_content(),
                'emotion': diary.emotion,
                'emotion_score': diary.emotion_score,
                'location_name': diary.location_name,
                'latitude': diary.latitude,
                'longitude': diary.longitude,
                'created_at': diary.created_at.isoformat(),
                'updated_at': diary.updated_at.isoformat(),
            })
        
        return Response({
            'exported_at': timezone.now().isoformat(),
            'total_diaries': len(result),
            'diaries': result
        })

    @action(detail=False, methods=['get'], url_path='locations')
    def locations(self, request):
        """
        위치 정보가 있는 일기들을 반환합니다 (지도 뷰용).
        """
        diaries = Diary.objects.filter(
            user=request.user,
            latitude__isnull=False,
            longitude__isnull=False
        ).order_by('-created_at')
        
        result = []
        for diary in diaries:
            result.append({
                'id': diary.id,
                'title': diary.title,
                'location_name': diary.location_name,
                'latitude': diary.latitude,
                'longitude': diary.longitude,
                'emotion': diary.emotion,
                'emotion_emoji': diary.get_emotion_display_emoji(),
                'created_at': diary.created_at.strftime('%Y-%m-%d'),
            })
        
        return Response({
            'total_locations': len(result),
            'locations': result
        })

    @action(detail=False, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request):
        """
        사용자의 모든 일기를 PDF 파일로 내보냅니다.
        """
        from django.http import HttpResponse
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        
        diaries = Diary.objects.filter(user=request.user).order_by('-created_at')
        
        # PDF 버퍼 생성
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 스타일 설정
        styles = getSampleStyleSheet()
        
        # 커스텀 스타일 (한글 지원을 위해 기본 폰트 사용)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # 중앙 정렬
        )
        
        diary_title_style = ParagraphStyle(
            'DiaryTitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            leading=16,
        )
        
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.gray,
            spaceAfter=5,
        )
        
        # 문서 내용 구성
        elements = []
        
        # 제목
        elements.append(Paragraph("My Diary Export", title_style))
        elements.append(Paragraph(
            f"Exported on {timezone.now().strftime('%Y-%m-%d %H:%M')} | Total: {diaries.count()} entries",
            date_style
        ))
        elements.append(Spacer(1, 1*cm))
        
        # 감정 이모지 매핑
        emotion_map = {
            'happy': 'Happy', 'sad': 'Sad', 'angry': 'Angry',
            'anxious': 'Anxious', 'peaceful': 'Peaceful',
            'excited': 'Excited', 'tired': 'Tired', 'love': 'Love'
        }
        
        # 각 일기 추가
        for diary in diaries:
            # 날짜
            date_str = diary.created_at.strftime('%Y-%m-%d %H:%M')
            emotion_str = emotion_map.get(diary.emotion, '') if diary.emotion else ''
            location_str = f" | Location: {diary.location_name}" if diary.location_name else ""
            
            elements.append(Paragraph(
                f"{date_str} | {emotion_str}{location_str}",
                date_style
            ))
            
            # 제목
            # HTML 특수문자 이스케이프
            safe_title = diary.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            elements.append(Paragraph(safe_title, diary_title_style))
            
            # 내용
            content = diary.decrypt_content()
            # HTML 특수문자 이스케이프 및 줄바꿈 처리
            safe_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_content = safe_content.replace('\n', '<br/>')
            elements.append(Paragraph(safe_content, content_style))
            
            # 구분선
            elements.append(Spacer(1, 0.5*cm))
        
        # PDF 생성
        doc.build(elements)
        
        # 응답 생성
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"diary_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    def generate_image(self, request, pk=None):
        """
        특정 일기 항목에 대한 AI 이미지를 생성합니다.
        """
        diary = self.get_object()
        
        # Check if the user owns this diary
        if diary.user != request.user:
            return Response(
                {'error': 'You do not have permission to access this diary.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            generator = ImageGenerator()
            result = generator.generate(diary.content)
            
            diary_image = DiaryImage.objects.create(
                diary=diary,
                image_url=result['url'],
                ai_prompt=result['prompt']
            )
            
            serializer = DiaryImageSerializer(diary_image)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranscribeView(APIView):
    """
    음성을 텍스트로 변환하는 API 뷰입니다.
    Whisper API를 사용하여 100개 이상의 언어를 지원합니다.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        음성 파일을 텍스트로 변환합니다.
        
        Request:
            - audio: 오디오 파일 (mp3, mp4, mpeg, mpga, m4a, wav, webm)
            - language: 언어 코드 (선택, 기본값: 'ko')
                       빈 문자열이면 자동 감지
        
        Response:
            {
                "text": "변환된 텍스트",
                "language": "사용된 언어 코드"
            }
        """
        audio_file = request.FILES.get('audio')
        
        if not audio_file:
            return Response(
                {'error': '오디오 파일이 필요합니다. "audio" 필드로 파일을 업로드해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 지원되는 오디오 형식 확인
        allowed_extensions = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
        file_extension = audio_file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            return Response(
                {'error': f'지원되지 않는 파일 형식입니다. 지원 형식: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 언어 파라미터 처리
        language = request.data.get('language', 'ko')
        if language == '':  # 빈 문자열이면 자동 감지
            language = None
        
        try:
            stt = SpeechToText()
            result = stt.transcribe(audio_file, language)
            
            return Response({
                'text': result['text'],
                'language': result['language']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'음성 변환 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranslateAudioView(APIView):
    """
    비영어 음성을 영어로 번역하는 API 뷰입니다.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        비영어 음성을 영어 텍스트로 번역합니다.
        
        Request:
            - audio: 오디오 파일
        
        Response:
            {
                "text": "영어로 번역된 텍스트",
                "original_language": "원본 언어 (자동 감지)"
            }
        """
        audio_file = request.FILES.get('audio')
        
        if not audio_file:
            return Response(
                {'error': '오디오 파일이 필요합니다. "audio" 필드로 파일을 업로드해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stt = SpeechToText()
            result = stt.translate_to_english(audio_file)
            
            return Response({
                'text': result['text'],
                'original_language': result['original_language']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'음성 번역 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SupportedLanguagesView(APIView):
    """
    음성-텍스트 변환에서 지원하는 언어 목록을 반환합니다.
    """
    
    def get(self, request):
        """
        지원되는 주요 언어 목록을 반환합니다.
        
        Response:
            {
                "languages": {"ko": "한국어", "en": "English", ...},
                "note": "Whisper는 100개 이상의 언어를 지원합니다..."
            }
        """
        return Response({
            'languages': SpeechToText.get_supported_languages(),
            'note': 'Whisper는 총 100개 이상의 언어를 지원합니다. 위 목록은 주요 언어입니다. language 파라미터를 비워두면 자동으로 언어를 감지합니다.'
        }, status=status.HTTP_200_OK)


class PushTokenView(APIView):
    """
    푸시 토큰 관리 API
    
    POST: 푸시 토큰 등록
    DELETE: 푸시 토큰 해제
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        푸시 토큰 등록
        
        Request Body:
            {
                "token": "ExponentPushToken[xxxxx]",
                "device_type": "android" | "ios",
                "device_name": "Samsung Galaxy S21" (선택)
            }
        
        Response:
            {
                "message": "푸시 토큰이 등록되었습니다.",
                "token_id": 1
            }
        """
        from .models import PushToken
        
        token = request.data.get('token')
        device_type = request.data.get('device_type', 'android')
        device_name = request.data.get('device_name', '')
        
        if not token:
            return Response(
                {'error': '푸시 토큰이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 토큰이 있으면 업데이트, 없으면 생성
        push_token, created = PushToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_type': device_type,
                'device_name': device_name,
                'is_active': True,
            }
        )
        
        action = '등록' if created else '업데이트'
        return Response({
            'message': f'푸시 토큰이 {action}되었습니다.',
            'token_id': push_token.id,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    def delete(self, request):
        """
        푸시 토큰 비활성화
        
        Request Body:
            {
                "token": "ExponentPushToken[xxxxx]"
            }
        
        Response:
            {
                "message": "푸시 알림이 비활성화되었습니다."
            }
        """
        from .models import PushToken
        
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'error': '푸시 토큰이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 토큰 비활성화
        updated = PushToken.objects.filter(
            token=token,
            user=request.user
        ).update(is_active=False)
        
        if updated:
            return Response({
                'message': '푸시 알림이 비활성화되었습니다.',
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': '해당 토큰을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )