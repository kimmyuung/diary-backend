# diary/views/ai_views.py
"""
AI 관련 API 뷰
- 일기 요약
- 제목 제안
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..ai_service import DiarySummarizer
from config.throttling import AIImageGenerationThrottle


class SummarizeView(APIView):
    """
    일기 내용 요약 API
    
    저장 전 일기 내용을 요약하여 미리보기 제공.
    사용자는 원본 또는 요약 중 선택하여 저장할 수 있음.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIImageGenerationThrottle]  # 일당 20회 제한 (AI API 비용)
    
    def post(self, request):
        """
        일기 내용을 요약합니다 (저장하지 않음).
        
        POST /api/summarize/
        
        Request Body:
            {
                "content": "오늘은 정말 좋은 하루였다. 아침에 일어나서...",
                "style": "default"  // "default", "short", "bullet" 중 선택 (선택사항)
            }
        
        Response:
            {
                "original_content": "오늘은 정말 좋은 하루였다. 아침에...",
                "summary": "좋은 아침으로 시작한 하루. 친구와 만남...",
                "original_length": 500,
                "summary_length": 150,
                "style": "default"
            }
        
        사용자는 응답을 받은 후:
        - 원본으로 저장: /api/diaries/ POST에 original_content 사용
        - 요약으로 저장: /api/diaries/ POST에 summary 사용
        """
        content = request.data.get('content', '').strip()
        style = request.data.get('style', 'default')
        
        if not content:
            return Response(
                {'error': '요약할 일기 내용을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(content) < 10:
            return Response(
                {'error': '요약하기에 내용이 너무 짧습니다. 10자 이상 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_styles = ['default', 'short', 'bullet']
        if style not in valid_styles:
            style = 'default'
        
        try:
            summarizer = DiarySummarizer()
            result = summarizer.summarize(content, style)
            
            return Response({
                'original_content': content,
                'summary': result['summary'],
                'original_length': result['original_length'],
                'summary_length': result['summary_length'],
                'style': result['style']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'요약 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuggestTitleView(APIView):
    """
    일기 제목 제안 API
    
    일기 내용을 기반으로 적절한 제목을 AI가 제안합니다.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIImageGenerationThrottle]
    
    def post(self, request):
        """
        일기 내용을 기반으로 제목을 제안합니다.
        
        POST /api/suggest-title/
        
        Request Body:
            {
                "content": "오늘은 오랜만에 친구들과 만나서..."
            }
        
        Response:
            {
                "suggested_title": "오랜만의 친구와의 만남"
            }
        """
        content = request.data.get('content', '').strip()
        
        if not content:
            return Response(
                {'error': '제목을 제안할 일기 내용을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            summarizer = DiarySummarizer()
            title = summarizer.suggest_title(content)
            
            return Response({
                'suggested_title': title
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'제목 제안 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
