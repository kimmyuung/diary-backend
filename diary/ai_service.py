# diary/ai_service.py (새 함수 추가)
import openai
import logging
from django.conf import settings

logger = logging.getLogger('diary')

class ImageGenerator:
    def generate(self, diary_content):
        """DALL-E를 사용하여 일기 내용에 맞는 이미지를 생성합니다."""
        logger.debug(f"Generating image for: {diary_content[:50]}...")
        
        try:
            # AI가 생성할 이미지에 대한 프롬프트를 구성합니다.
            prompt = (
                "An emotional and abstract illustration representing the following diary entry. "
                "The style should be peaceful, visually striking, and artistic. "
                f"Diary snippet: '{diary_content[:150]}'"
            )
            
            # OpenAI API를 호출하여 이미지를 생성합니다.
            response = openai.Image.create(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"Image generated successfully: {image_url}")
            
            # 뷰에서 사용할 수 있도록 URL과 프롬프트를 딕셔너리로 반환합니다.
            return {
                'url': image_url,
                'prompt': prompt
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error during image generation: {e}")
            # 에러를 다시 발생시켜 상위 호출자(뷰)에서 처리할 수 있도록 합니다.
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during image generation: {e}")
            raise e

class SpeechToText:
    """
    OpenAI Whisper API를 사용한 음성-텍스트 변환 서비스.
    100개 이상의 언어를 지원합니다.
    """
    
    # 지원되는 주요 언어 목록 (ISO 639-1 코드)
    SUPPORTED_LANGUAGES = {
        'ko': '한국어',
        'en': 'English',
        'ja': '日本語',
        'zh': '中文',
        'es': 'Español',
        'fr': 'Français',
        'de': 'Deutsch',
        'pt': 'Português',
        'it': 'Italiano',
        'ru': 'Русский',
        'ar': 'العربية',
        'hi': 'हिन्दी',
        'th': 'ไทย',
        'vi': 'Tiếng Việt',
    }
    
    def transcribe(self, audio_file, language='ko'):
        """
        음성 파일을 텍스트로 변환합니다.
        
        Args:
            audio_file: 오디오 파일 객체 (mp3, mp4, mpeg, mpga, m4a, wav, webm 지원)
            language: 언어 코드 (기본값: 'ko' 한국어)
                     None으로 설정하면 자동 감지
        
        Returns:
            dict: {
                'text': 변환된 텍스트,
                'language': 사용된 언어 코드
            }
        """
        logger.debug(f"Transcribing audio with language: {language}")
        
        try:
            # OpenAI Whisper API 호출
            transcription_params = {
                'model': 'whisper-1',
                'file': audio_file,
            }
            
            # 언어가 지정된 경우에만 language 파라미터 추가
            # (지정하지 않으면 Whisper가 자동 감지)
            if language:
                transcription_params['language'] = language
            
            response = openai.Audio.transcribe(**transcription_params)
            
            text = response.text if hasattr(response, 'text') else response['text']
            
            logger.info(f"Audio transcribed successfully. Length: {len(text)} characters")
            
            return {
                'text': text,
                'language': language or 'auto-detected'
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error during transcription: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during transcription: {e}")
            raise e
    
    def translate_to_english(self, audio_file):
        """
        비영어 음성을 영어 텍스트로 번역합니다.
        
        Args:
            audio_file: 오디오 파일 객체
        
        Returns:
            dict: {
                'text': 영어로 번역된 텍스트,
                'original_language': 원본 언어 (자동 감지)
            }
        """
        logger.debug("Translating audio to English")
        
        try:
            response = openai.Audio.translate(
                model='whisper-1',
                file=audio_file,
            )
            
            text = response.text if hasattr(response, 'text') else response['text']
            
            logger.info(f"Audio translated successfully. Length: {len(text)} characters")
            
            return {
                'text': text,
                'original_language': 'auto-detected'
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error during translation: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during translation: {e}")
            raise e
    
    @classmethod
    def get_supported_languages(cls):
        """지원되는 주요 언어 목록을 반환합니다."""
        return cls.SUPPORTED_LANGUAGES


class DiarySummarizer:
    """
    일기 내용을 AI로 요약하는 서비스
    GPT-4o-mini를 사용하여 일기 내용을 간결하게 요약합니다.
    """
    
    def summarize(self, content: str, style: str = 'default') -> dict:
        """
        일기 내용을 요약합니다.
        
        Args:
            content: 원본 일기 내용
            style: 요약 스타일 
                - 'default': 기본 3줄 요약
                - 'short': 1줄 요약
                - 'bullet': 핵심 포인트 불릿
        
        Returns:
            dict: {
                'summary': 요약된 내용,
                'original_length': 원본 글자 수,
                'summary_length': 요약 글자 수,
                'style': 사용된 스타일
            }
        """
        logger.debug(f"Summarizing diary content with style: {style}")
        
        if not content or len(content.strip()) < 10:
            return {
                'summary': content,
                'original_length': len(content),
                'summary_length': len(content),
                'style': style,
                'error': '요약하기에 내용이 너무 짧습니다.'
            }
        
        # 스타일별 프롬프트 설정
        style_prompts = {
            'default': """다음 일기 내용을 3줄로 간결하게 요약해주세요.
- 핵심 내용과 감정을 포함해주세요.
- 일기의 분위기를 유지해주세요.
- 요약만 반환하고 다른 설명은 하지 마세요.""",
            
            'short': """다음 일기 내용을 한 문장으로 아주 간결하게 요약해주세요.
- 가장 중요한 핵심만 포함해주세요.
- 요약만 반환하세요.""",
            
            'bullet': """다음 일기 내용의 핵심 포인트를 불릿 형식으로 정리해주세요.
- 3-5개의 핵심 포인트
- 각 포인트는 간결하게
- "• " 기호로 시작하세요."""
        }
        
        prompt = style_prompts.get(style, style_prompts['default'])
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 일기 내용을 요약하는 전문가입니다. 사용자의 감정과 경험을 존중하며 핵심을 잘 파악합니다."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n일기 내용:\n{content}"
                    }
                ],
                temperature=0.5,
                max_tokens=300,
            )
            
            summary = response.choices[0].message.content.strip()
            
            logger.info(f"Diary summarized successfully. Original: {len(content)} chars, Summary: {len(summary)} chars")
            
            return {
                'summary': summary,
                'original_length': len(content),
                'summary_length': len(summary),
                'style': style
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error during summarization: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during summarization: {e}")
            raise e
    
    def suggest_title(self, content: str) -> str:
        """
        일기 내용을 기반으로 제목을 제안합니다.
        
        Args:
            content: 일기 내용
            
        Returns:
            str: 제안된 제목
        """
        logger.debug("Suggesting title for diary content")
        
        if not content or len(content.strip()) < 10:
            return "오늘의 일기"
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "일기 내용을 보고 적절한 제목을 제안해주세요. 제목만 반환하세요. 15자 이내로 작성하세요."
                    },
                    {
                        "role": "user",
                        "content": content[:500]  # 처음 500자만 사용
                    }
                ],
                temperature=0.7,
                max_tokens=50,
            )
            
            title = response.choices[0].message.content.strip()
            # 따옴표 제거
            title = title.strip('"\'')
            
            logger.info(f"Title suggested: {title}")
            return title
            
        except Exception as e:
            logger.error(f"Error suggesting title: {e}")
            return "오늘의 일기"


class TemplateGenerator:
    """
    AI를 사용하여 일기 템플릿을 생성하는 서비스.
    사용자가 주제를 입력하면 맞춤형 템플릿을 생성합니다.
    """
    
    def generate(self, topic: str, style: str = 'default') -> dict:
        """
        주제에 맞는 일기 템플릿을 생성합니다.
        
        Args:
            topic: 템플릿 주제 (예: "독서 일기", "요리 기록")
            style: 스타일 (default, simple, detailed)
            
        Returns:
            dict: {
                'name': 템플릿 이름,
                'emoji': 템플릿 아이콘,
                'description': 템플릿 설명,
                'content': 템플릿 내용
            }
        """
        logger.debug(f"Generating template for topic: {topic}, style: {style}")
        
        if not topic or len(topic.strip()) < 2:
            raise ValueError("주제를 2자 이상 입력해주세요.")
        
        style_instruction = {
            'default': '적당한 길이로 작성하세요.',
            'simple': '간단하고 짧게 작성하세요. 3-4개 항목만 포함하세요.',
            'detailed': '자세하고 구체적으로 작성하세요. 다양한 항목을 포함하세요.',
        }.get(style, '적당한 길이로 작성하세요.')
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""당신은 일기 템플릿을 만드는 전문가입니다.
사용자가 원하는 주제에 맞는 일기 템플릿을 만들어주세요.

{style_instruction}

다음 JSON 형식으로만 응답하세요:
{{
    "name": "템플릿 이름 (최대 15자)",
    "emoji": "대표 이모지 1개",
    "description": "템플릿 설명 (최대 50자)",
    "content": "템플릿 내용 (줄바꿈 포함)"
}}

템플릿 내용 규칙:
- 이모지를 활용하여 각 섹션을 구분하세요
- 사용자가 채울 부분은 빈 줄로 남겨두세요
- 항목은 질문 형식으로 작성하세요
- 한국어로 작성하세요"""
                    },
                    {
                        "role": "user",
                        "content": f"'{topic}' 주제의 일기 템플릿을 만들어주세요."
                    }
                ],
                temperature=0.8,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            import json
            # 코드 블록 제거
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            
            # 유효성 검사
            required_keys = ['name', 'emoji', 'description', 'content']
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing key: {key}")
            
            logger.info(f"Template generated: {result['name']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            # 폴백: 기본 템플릿 반환
            return {
                'name': topic[:15],
                'emoji': '📝',
                'description': f'{topic} 일기를 작성합니다',
                'content': f'{topic}\n\n오늘의 기록:\n\n\n느낀 점:\n\n\n내일 할 것:\n'
            }
            
        except Exception as e:
            logger.error(f"Error generating template: {e}")
            raise e


openai.api_key = settings.OPENAI_API_KEY
