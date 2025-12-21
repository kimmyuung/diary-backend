# diary/views/diary_views.py
"""
일기(Diary) 관련 API 뷰
- 일기 CRUD
- 감정 리포트
- 캘린더
- 갤러리
- 내보내기 (JSON/PDF)
- 위치 기반 일기
- AI 이미지 생성
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, datetime

from ..models import Diary, DiaryImage
from ..serializers import DiarySerializer, DiaryImageSerializer
from ..ai_service import ImageGenerator


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
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        
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

    @action(detail=False, methods=['get'], url_path='heatmap')
    def heatmap(self, request):
        """
        GitHub 잔디 스타일의 감정 히트맵 데이터를 반환합니다.
        
        Query Parameters:
            - year: 연도 (기본값: 현재 연도)
        
        Response:
            {
                "year": 2024,
                "total_entries": 145,
                "streak": {
                    "current": 7,
                    "longest": 23
                },
                "emotion_colors": {
                    "happy": "#FFD93D",
                    "sad": "#6B7FD7",
                    ...
                },
                "data": {
                    "2024-01-01": {"count": 1, "emotion": "happy", "color": "#FFD93D"},
                    "2024-01-02": null,
                    ...
                },
                "monthly_summary": [
                    {"month": 1, "count": 15, "dominant_emotion": "happy"},
                    ...
                ]
            }
        """
        from datetime import date
        from collections import defaultdict
        
        now = timezone.now()
        year = request.query_params.get('year', now.year)
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {"error": "유효하지 않은 연도입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 감정별 색상 매핑
        emotion_colors = {
            'happy': '#FFD93D',      # 노란색
            'sad': '#6B7FD7',        # 파란색
            'angry': '#FF6B6B',      # 빨간색
            'anxious': '#9B59B6',    # 보라색
            'peaceful': '#4ECDC4',   # 초록색
            'excited': '#FF9F43',    # 주황색
            'tired': '#95A5A6',      # 회색
            'love': '#FF6B9D',       # 핑크색
            None: '#E8E8E8',         # 기본 (감정 없음)
        }
        
        # 해당 연도의 일기 조회
        diaries = Diary.objects.filter(
            user=request.user,
            created_at__year=year
        ).order_by('created_at')
        
        # 날짜별 데이터 집계
        date_data = defaultdict(lambda: {'count': 0, 'emotions': []})
        
        for diary in diaries:
            date_str = diary.created_at.strftime('%Y-%m-%d')
            date_data[date_str]['count'] += 1
            if diary.emotion:
                date_data[date_str]['emotions'].append(diary.emotion)
        
        # 1년 전체 데이터 생성 (없는 날짜는 null)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        current_date = start_date
        
        heatmap_data = {}
        all_dates_with_entries = []
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in date_data:
                entry = date_data[date_str]
                # 가장 많이 기록된 감정을 대표 감정으로
                dominant_emotion = None
                if entry['emotions']:
                    emotion_counts = defaultdict(int)
                    for em in entry['emotions']:
                        emotion_counts[em] += 1
                    dominant_emotion = max(emotion_counts, key=emotion_counts.get)
                
                heatmap_data[date_str] = {
                    'count': entry['count'],
                    'emotion': dominant_emotion,
                    'color': emotion_colors.get(dominant_emotion, emotion_colors[None])
                }
                all_dates_with_entries.append(current_date)
            else:
                heatmap_data[date_str] = None
            
            current_date += timedelta(days=1)
        
        # 연속 작성일 계산
        def calculate_streaks(dates_list):
            if not dates_list:
                return 0, 0
            
            sorted_dates = sorted(dates_list)
            current_streak = 1
            longest_streak = 1
            temp_streak = 1
            
            for i in range(1, len(sorted_dates)):
                diff = (sorted_dates[i] - sorted_dates[i-1]).days
                if diff == 1:
                    temp_streak += 1
                    longest_streak = max(longest_streak, temp_streak)
                elif diff > 1:
                    temp_streak = 1
            
            # 현재 연속 작성일 (오늘 기준)
            today = now.date()
            if today in sorted_dates:
                current_streak = 1
                idx = sorted_dates.index(today)
                for i in range(idx - 1, -1, -1):
                    if (sorted_dates[i + 1] - sorted_dates[i]).days == 1:
                        current_streak += 1
                    else:
                        break
            else:
                current_streak = 0
            
            return current_streak, longest_streak
        
        current_streak, longest_streak = calculate_streaks(all_dates_with_entries)
        
        # 월별 요약
        monthly_summary = []
        for month in range(1, 13):
            month_diaries = diaries.filter(created_at__month=month)
            month_count = month_diaries.count()
            
            dominant_emotion = None
            dominant_color = emotion_colors[None]
            
            if month_count > 0:
                emotion_counts = month_diaries.filter(
                    emotion__isnull=False
                ).values('emotion').annotate(
                    count=Count('emotion')
                ).order_by('-count').first()
                
                if emotion_counts:
                    dominant_emotion = emotion_counts['emotion']
                    dominant_color = emotion_colors.get(dominant_emotion, emotion_colors[None])
            
            monthly_summary.append({
                'month': month,
                'count': month_count,
                'dominant_emotion': dominant_emotion,
                'color': dominant_color
            })
        
        return Response({
            'year': year,
            'total_entries': diaries.count(),
            'streak': {
                'current': current_streak,
                'longest': longest_streak
            },
            'emotion_colors': emotion_colors,
            'data': heatmap_data,
            'monthly_summary': monthly_summary
        })
