# diary/management/commands/create_system_templates.py
"""
시스템 기본 템플릿을 생성하는 관리 명령어

사용법:
    python manage.py create_system_templates
"""
from django.core.management.base import BaseCommand
from diary.models import DiaryTemplate


class Command(BaseCommand):
    help = '시스템 기본 일기 템플릿을 생성합니다'

    def handle(self, *args, **options):
        templates = [
            {
                'name': '오늘 하루',
                'emoji': '📅',
                'category': 'daily',
                'description': '일반적인 하루 일기를 작성합니다',
                'content': '''오늘은 어떤 하루였나요?

🌅 아침:


☀️ 낮:


🌙 저녁:


💭 오늘의 한마디:
'''
            },
            {
                'name': '감사 일기',
                'emoji': '🙏',
                'category': 'gratitude',
                'description': '오늘 감사한 것들을 기록합니다',
                'content': '''오늘 감사한 세 가지

1. 

2. 

3. 


왜 감사한가요?


이 감사함을 어떻게 표현할 수 있을까요?
'''
            },
            {
                'name': '목표 일기',
                'emoji': '🎯',
                'category': 'goal',
                'description': '목표 달성 현황을 기록합니다',
                'content': '''📌 오늘의 목표:


✅ 달성한 것:


❌ 미달성:


💡 이유와 개선점:


📋 내일 할 일:
'''
            },
            {
                'name': '주간 회고',
                'emoji': '💭',
                'category': 'reflection',
                'description': '일주일을 돌아보며 정리합니다',
                'content': '''# 이번 주 회고

## 🎉 잘한 것


## 😅 아쉬운 점


## 📚 배운 것


## 🎯 다음 주 목표


## 💬 스스로에게 한마디
'''
            },
            {
                'name': '성장 일기',
                'emoji': '🌟',
                'category': 'reflection',
                'description': '오늘 배우고 성장한 것을 기록합니다',
                'content': '''오늘 배운 것:


느낀 점:


내일 적용할 점:


관련 자료/링크:
'''
            },
            {
                'name': '감정 일기',
                'emoji': '😊',
                'category': 'emotion',
                'description': '오늘의 감정을 깊이 탐구합니다',
                'content': '''지금 기분은 어때요?


왜 이런 기분이 드나요?


이 감정이 내게 말해주는 것은?


어떻게 하면 더 좋아질 수 있을까요?


스스로에게 해주고 싶은 말:
'''
            },
            {
                'name': '여행 일기',
                'emoji': '✈️',
                'category': 'travel',
                'description': '여행의 순간을 기록합니다',
                'content': '''📍 장소:


🚗 이동 수단:


🍽️ 먹은 것:


📸 기억에 남는 순간:


💰 오늘 지출:


✨ 특별했던 점:
'''
            },
            {
                'name': '운동 일기',
                'emoji': '🏃',
                'category': 'exercise',
                'description': '운동과 건강 기록을 남깁니다',
                'content': '''🏋️ 운동 종류:


⏱️ 운동 시간:


🔥 강도: □ 낮음  □ 보통  □ 높음


💪 컨디션: /10


📏 체중/기록:


📝 메모:
'''
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            obj, created = DiaryTemplate.objects.update_or_create(
                template_type='system',
                name=template_data['name'],
                defaults={
                    'emoji': template_data['emoji'],
                    'category': template_data['category'],
                    'description': template_data['description'],
                    'content': template_data['content'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ 생성: {obj.emoji} {obj.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"  🔄 업데이트: {obj.emoji} {obj.name}"))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'완료! 생성: {created_count}개, 업데이트: {updated_count}개'
        ))
