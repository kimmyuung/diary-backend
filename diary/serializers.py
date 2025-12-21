# diary/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Diary, DiaryImage


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    회원가입 Serializer
    - 사용자명, 이메일, 비밀번호 필수
    - 비밀번호 확인 검증
    - Django 비밀번호 검증 적용
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate_username(self, value):
        """사용자명 중복 확인"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return value

    def validate_email(self, value):
        """이메일 중복 확인"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 등록된 이메일입니다.")
        return value

    def validate(self, attrs):
        """비밀번호 확인 검증"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "비밀번호가 일치하지 않습니다."
            })
        return attrs

    def create(self, validated_data):
        """사용자 생성"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class DiaryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryImage
        fields = ['id', 'image_url', 'ai_prompt', 'created_at']


class DiarySerializer(serializers.ModelSerializer):
    """
    일기 Serializer
    - 저장 시 내용 암호화 + 감정 분석
    - 조회 시 내용 복호화
    """
    images = DiaryImageSerializer(many=True, read_only=True)
    emotion_emoji = serializers.SerializerMethodField()
    
    class Meta:
        model = Diary
        fields = [
            'id', 'user', 'title', 'content', 'images',
            'emotion', 'emotion_score', 'emotion_emoji', 'emotion_analyzed_at',
            'location_name', 'latitude', 'longitude',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'updated_at', 'emotion', 'emotion_score', 'emotion_analyzed_at']
    
    def get_emotion_emoji(self, obj):
        """감정 이모지 반환"""
        return obj.get_emotion_display_emoji() if obj.emotion else None
    
    def to_representation(self, instance):
        """조회 시 암호화된 내용을 복호화하여 반환"""
        data = super().to_representation(instance)
        data['content'] = instance.decrypt_content()
        return data
    
    def create(self, validated_data):
        """생성 시 내용 암호화 + 감정 분석"""
        plain_content = validated_data.pop('content', '')
        instance = Diary(**validated_data)
        instance.encrypt_content(plain_content)
        instance.save()
        
        # 비동기로 감정 분석 (또는 동기로 바로 실행)
        try:
            from .emotion_service import analyze_diary_emotion
            analyze_diary_emotion(instance)
        except Exception as e:
            import logging
            logging.getLogger('diary').error(f"Emotion analysis failed: {e}")
        
        return instance
    
    def update(self, instance, validated_data):
        """수정 시 내용 암호화 + 감정 재분석"""
        content_changed = False
        
        if 'content' in validated_data:
            plain_content = validated_data.pop('content')
            instance.encrypt_content(plain_content)
            content_changed = True
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # 내용이 변경되면 감정 재분석
        if content_changed:
            try:
                from .emotion_service import analyze_diary_emotion
                analyze_diary_emotion(instance)
            except Exception as e:
                import logging
                logging.getLogger('diary').error(f"Emotion analysis failed: {e}")
        
        return instance

