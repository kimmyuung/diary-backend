# diary/views/template_views.py
"""
일기 템플릿 API 뷰
- 시스템 템플릿 조회
- 사용자 커스텀 템플릿 CRUD
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q

from ..models import DiaryTemplate
from ..serializers import DiaryTemplateSerializer


class DiaryTemplateViewSet(viewsets.ModelViewSet):
    """
    일기 템플릿 ViewSet
    - 시스템 템플릿 + 본인 템플릿 조회
    - 커스텀 템플릿 생성/수정/삭제
    """
    serializer_class = DiaryTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자가 접근 가능한 템플릿만 반환"""
        user = self.request.user
        return DiaryTemplate.objects.filter(
            Q(template_type='system') | Q(user=user),
            is_active=True
        ).order_by('-use_count', 'name')
    
    def perform_create(self, serializer):
        """템플릿 생성 시 사용자 할당"""
        serializer.save(user=self.request.user, template_type='user')
    
    def destroy(self, request, *args, **kwargs):
        """시스템 템플릿은 삭제 불가"""
        instance = self.get_object()
        if instance.template_type == 'system':
            return Response(
                {'error': '시스템 템플릿은 삭제할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if instance.user != request.user:
            return Response(
                {'error': '본인이 생성한 템플릿만 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """시스템 템플릿은 수정 불가"""
        instance = self.get_object()
        if instance.template_type == 'system':
            return Response(
                {'error': '시스템 템플릿은 수정할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if instance.user != request.user:
            return Response(
                {'error': '본인이 생성한 템플릿만 수정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='use')
    def use_template(self, request, pk=None):
        """
        템플릿 사용 (사용 횟수 증가)
        
        POST /api/templates/{id}/use/
        
        Response:
            {
                "id": 1,
                "name": "오늘 하루",
                "content": "오늘은 어떤 하루였나요?...",
                "use_count": 11
            }
        """
        template = self.get_object()
        template.increment_use_count()
        
        return Response({
            'id': template.id,
            'name': template.name,
            'emoji': template.emoji,
            'content': template.content,
            'use_count': template.use_count,
            'message': f"'{template.name}' 템플릿이 적용되었습니다."
        })
    
    @action(detail=False, methods=['get'], url_path='system')
    def system_templates(self, request):
        """
        시스템 템플릿만 조회
        
        GET /api/templates/system/
        """
        templates = DiaryTemplate.objects.filter(
            template_type='system',
            is_active=True
        ).order_by('-use_count', 'name')
        
        serializer = self.get_serializer(templates, many=True)
        return Response({
            'count': templates.count(),
            'templates': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_templates(self, request):
        """
        내 커스텀 템플릿만 조회
        
        GET /api/templates/my/
        """
        templates = DiaryTemplate.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-use_count', 'name')
        
        serializer = self.get_serializer(templates, many=True)
        return Response({
            'count': templates.count(),
            'templates': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='popular')
    def popular_templates(self, request):
        """
        인기 템플릿 (상위 10개)
        
        GET /api/templates/popular/
        """
        templates = self.get_queryset().order_by('-use_count')[:10]
        serializer = self.get_serializer(templates, many=True)
        
        return Response({
            'templates': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='by-category/(?P<category>[^/.]+)')
    def by_category(self, request, category=None):
        """
        카테고리별 템플릿 조회
        
        GET /api/templates/by-category/daily/
        """
        templates = self.get_queryset().filter(category=category)
        serializer = self.get_serializer(templates, many=True)
        
        return Response({
            'category': category,
            'count': templates.count(),
            'templates': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_template(self, request):
        """
        AI로 템플릿 생성
        
        POST /api/templates/generate/
        
        Request Body:
            {
                "topic": "독서 일기",
                "style": "default" | "simple" | "detailed" (선택)
            }
        
        Response:
            {
                "name": "독서 일기",
                "emoji": "📚",
                "description": "책을 읽고 느낀 점을 기록합니다",
                "content": "📚 오늘 읽은 책:\n\n...",
                "message": "템플릿이 생성되었습니다."
            }
        """
        from ..ai_service import TemplateGenerator
        from config.throttling import AIImageGenerationThrottle
        
        topic = request.data.get('topic', '').strip()
        style = request.data.get('style', 'default')
        
        if not topic:
            return Response(
                {'error': '주제를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(topic) < 2:
            return Response(
                {'error': '주제를 2자 이상 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(topic) > 50:
            return Response(
                {'error': '주제는 50자 이하로 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            generator = TemplateGenerator()
            result = generator.generate(topic, style)
            
            return Response({
                **result,
                'message': '템플릿이 생성되었습니다. 저장하려면 "템플릿 저장"을 눌러주세요.'
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': '템플릿 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='save-generated')
    def save_generated_template(self, request):
        """
        AI로 생성된 템플릿을 저장
        
        POST /api/templates/save-generated/
        
        Request Body:
            {
                "name": "독서 일기",
                "emoji": "📚",
                "description": "책을 읽고 느낀 점을 기록합니다",
                "content": "📚 오늘 읽은 책:\n\n..."
            }
        """
        name = request.data.get('name', '').strip()
        emoji = request.data.get('emoji', '📝')
        description = request.data.get('description', '').strip()
        content = request.data.get('content', '').strip()
        
        if not name or not content:
            return Response(
                {'error': '이름과 내용은 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 중복 이름 체크
        if DiaryTemplate.objects.filter(user=request.user, name=name).exists():
            return Response(
                {'error': '이미 동일한 이름의 템플릿이 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        template = DiaryTemplate.objects.create(
            user=request.user,
            template_type='user',
            category='custom',
            name=name[:50],
            emoji=emoji[:10] if emoji else '📝',
            description=description[:200] if description else f'{name} 템플릿',
            content=content,
        )
        
        serializer = self.get_serializer(template)
        return Response({
            'template': serializer.data,
            'message': f"'{name}' 템플릿이 저장되었습니다."
        }, status=status.HTTP_201_CREATED)
