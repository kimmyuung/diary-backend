from django.db import models
from django.contrib.auth.models import User


class Diary(models.Model):
    """
    일기 모델
    - 내용은 암호화되어 저장됨
    - AI 감정 분석 결과 포함
    """
    
    # 감정 선택지
    EMOTION_CHOICES = [
        ('happy', '행복'),
        ('sad', '슬픔'),
        ('angry', '화남'),
        ('anxious', '불안'),
        ('peaceful', '평온'),
        ('excited', '신남'),
        ('tired', '피곤'),
        ('love', '사랑'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()  # 암호화된 상태로 저장
    is_encrypted = models.BooleanField(default=True)  # 암호화 여부
    
    # 감정 분석 필드
    emotion = models.CharField(
        max_length=20,
        choices=EMOTION_CHOICES,
        null=True,
        blank=True,
        verbose_name='감정'
    )
    emotion_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='감정 강도',
        help_text='0-100 사이의 값'
    )
    emotion_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='감정 분석 시간'
    )
    
    # 위치 정보 필드
    location_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='장소명'
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='위도'
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='경도'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '일기'
        verbose_name_plural = '일기들'
        indexes = [
            # 사용자별 최신 일기 조회 (가장 빈번한 쿼리)
            models.Index(fields=['user', '-created_at'], name='diary_user_created_idx'),
            # 감정별 필터링
            models.Index(fields=['user', 'emotion'], name='diary_user_emotion_idx'),
            # 날짜 범위 검색
            models.Index(fields=['created_at'], name='diary_created_at_idx'),
            # 위치 기반 검색
            models.Index(fields=['user', 'location_name'], name='diary_user_location_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def get_emotion_display_emoji(self) -> str:
        """감정에 해당하는 이모지 반환"""
        emoji_map = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😡',
            'anxious': '😰',
            'peaceful': '😌',
            'excited': '🥳',
            'tired': '😴',
            'love': '🥰',
        }
        return emoji_map.get(self.emotion, '')

    def encrypt_content(self, plain_content: str) -> None:
        """내용을 암호화하여 저장"""
        from .encryption import get_encryption_service
        service = get_encryption_service()
        if service.is_enabled:
            self.content = service.encrypt(plain_content)
            self.is_encrypted = True
        else:
            self.content = plain_content
            self.is_encrypted = False

    def decrypt_content(self) -> str:
        """암호화된 내용을 복호화하여 반환"""
        if not self.is_encrypted:
            return self.content
        
        from .encryption import get_encryption_service
        service = get_encryption_service()
        return service.decrypt(self.content)


class DiaryImage(models.Model):
    """AI 생성 이미지"""
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=500)
    ai_prompt = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.diary.id}"


class PasswordResetToken(models.Model):
    """
    비밀번호 재설정 토큰
    - 이메일로 전송되는 6자리 인증 코드
    - 30분 후 만료
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=6, verbose_name='인증 코드')  # 6자리 숫자
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='만료 시간')
    is_used = models.BooleanField(default=False, verbose_name='사용 여부')

    class Meta:
        verbose_name = '비밀번호 재설정 토큰'
        verbose_name_plural = '비밀번호 재설정 토큰들'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.token}"

    @property
    def is_expired(self):
        """토큰 만료 여부"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """토큰 유효성 (만료되지 않고 사용되지 않음)"""
        return not self.is_expired and not self.is_used

    @classmethod
    def generate_token(cls, user):
        """새 토큰 생성 (기존 토큰 무효화)"""
        import random
        from django.utils import timezone
        from datetime import timedelta

        # 기존 미사용 토큰 무효화
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # 6자리 랜덤 코드 생성
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # 30분 후 만료
        expires_at = timezone.now() + timedelta(minutes=30)

        return cls.objects.create(
            user=user,
            token=code,
            expires_at=expires_at
        )


class EmailVerificationToken(models.Model):
    """
    이메일 인증 토큰 (회원가입 시 이메일 인증용)
    - 6자리 인증 코드
    - 10분 후 만료
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    token = models.CharField(max_length=6, verbose_name='인증 코드')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='만료 시간')
    is_verified = models.BooleanField(default=False, verbose_name='인증 완료')

    class Meta:
        verbose_name = '이메일 인증 토큰'
        verbose_name_plural = '이메일 인증 토큰들'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.token}"

    @property
    def is_expired(self):
        """토큰 만료 여부"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """토큰 유효성"""
        return not self.is_expired and not self.is_verified

    @classmethod
    def generate_token(cls, user):
        """새 토큰 생성"""
        import random
        from django.utils import timezone
        from datetime import timedelta

        # 기존 미인증 토큰 삭제
        cls.objects.filter(user=user, is_verified=False).delete()

        # 6자리 랜덤 코드 생성
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # 10분 후 만료
        expires_at = timezone.now() + timedelta(minutes=10)

        return cls.objects.create(
            user=user,
            token=code,
            expires_at=expires_at
        )


class PushToken(models.Model):
    """
    푸시 알림 토큰 모델
    - 사용자별 Expo Push Token 저장
    - 기기별 토큰 관리
    """
    
    DEVICE_TYPES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='push_tokens'
    )
    token = models.CharField(
        max_length=200, 
        unique=True,
        verbose_name='Expo Push Token'
    )
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPES,
        default='android',
        verbose_name='기기 유형'
    )
    device_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='기기명'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '푸시 토큰'
        verbose_name_plural = '푸시 토큰들'
        ordering = ['-created_at']
        indexes = [
            # 활성 토큰 조회
            models.Index(fields=['user', 'is_active'], name='push_user_active_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} ({self.token[:20]}...)"

