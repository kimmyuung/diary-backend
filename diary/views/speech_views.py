# diary/views/speech_views.py
"""
음성 인식(Speech-to-Text) 관련 API 뷰
- 음성→텍스트 변환 (Whisper)
- 음성→영어 번역
- 지원 언어 목록
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..ai_service import SpeechToText
from config.throttling import TranscriptionRateThrottle


class TranscribeView(APIView):
    """
    음성을 텍스트로 변환하는 API 뷰입니다.
    Whisper API를 사용하여 100개 이상의 언어를 지원합니다.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [TranscriptionRateThrottle]  # 시간당 30회 제한 (API 비용 관리)
    
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
