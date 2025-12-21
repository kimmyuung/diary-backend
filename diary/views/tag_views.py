# diary/views/tag_views.py
"""
태그 관련 API 뷰
- 태그 CRUD
- 일기에 태그 추가/제거
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from ..models import Tag, DiaryTag
from ..serializers import TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    태그 ViewSet
    - 사용자별 태그 관리
    - CRUD 기능 제공
    """
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 태그만 반환"""
        return Tag.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """태그 생성 시 현재 사용자 할당"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'], url_path='diaries')
    def diaries(self, request, pk=None):
        """
        특정 태그가 적용된 일기 목록 조회
        
        GET /api/tags/{id}/diaries/
        """
        tag = self.get_object()
        diary_tags = DiaryTag.objects.filter(
            tag=tag
        ).select_related('diary').order_by('-diary__created_at')
        
        result = []
        for dt in diary_tags:
            diary = dt.diary
            result.append({
                'id': diary.id,
                'title': diary.title,
                'emotion': diary.emotion,
                'emotion_emoji': diary.get_emotion_display_emoji(),
                'created_at': diary.created_at.isoformat(),
            })
        
        return Response({
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color
            },
            'diary_count': len(result),
            'diaries': result
        })
    
    @action(detail=False, methods=['get'], url_path='popular')
    def popular(self, request):
        """
        자주 사용하는 태그 목록 (상위 10개)
        
        GET /api/tags/popular/
        """
        from django.db.models import Count
        
        tags = Tag.objects.filter(
            user=request.user
        ).annotate(
            usage_count=Count('diary_tags')
        ).order_by('-usage_count')[:10]
        
        result = []
        for tag in tags:
            result.append({
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'diary_count': tag.usage_count
            })
        
        return Response({
            'tags': result
        })
