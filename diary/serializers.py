# diary/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Diary, DiaryImage, Tag, DiaryTag, UserPreference, DiaryTemplate



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


class TagSerializer(serializers.ModelSerializer):
    """
    태그 Serializer
    """
    diary_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'diary_count', 'created_at']
        read_only_fields = ['created_at']
    
    def get_diary_count(self, obj):
        """해당 태그가 적용된 일기 수"""
        return obj.diary_tags.count()
    
    def validate_name(self, value):
        """태그명 중복 검사"""
        request = self.context.get('request')
        if request and request.user:
            # 수정 시에는 자기 자신은 제외
            instance = self.instance
            qs = Tag.objects.filter(user=request.user, name=value)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError("이미 동일한 이름의 태그가 있습니다.")
        return value
    
    def create(self, validated_data):
        """태그 생성 시 현재 사용자 자동 할당"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)



class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    사용자 설정 Serializer
    - 테마, 언어, 알림 등 개인화 설정
    """
    class Meta:
        model = UserPreference
        fields = [
            'theme', 'language',
            'push_enabled', 'daily_reminder_enabled', 'daily_reminder_time',
            'auto_emotion_analysis', 'show_location',
            'updated_at'
        ]
        read_only_fields = ['updated_at']


class DiarySerializer(serializers.ModelSerializer):
    """
    일기 Serializer
    - 저장 시 내용 암호화 + 감정 분석
    - 조회 시 내용 복호화
    """
    images = DiaryImageSerializer(many=True, read_only=True)
    emotion_emoji = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text='태그 ID 목록'
    )
    
    class Meta:
        model = Diary
        fields = [
            'id', 'user', 'title', 'content', 'images',
            'emotion', 'emotion_score', 'emotion_emoji', 'emotion_analyzed_at',
            'location_name', 'latitude', 'longitude',
            'tags', 'tag_ids',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'updated_at', 'emotion', 'emotion_score', 'emotion_analyzed_at']
    
    def get_emotion_emoji(self, obj):
        """감정 이모지 반환"""
        return obj.get_emotion_display_emoji() if obj.emotion else None
    
    def get_tags(self, obj):
        """일기에 연결된 태그 목록"""
        diary_tags = obj.diary_tags.select_related('tag').all()
        return [
            {
                'id': dt.tag.id,
                'name': dt.tag.name,
                'color': dt.tag.color
            }
            for dt in diary_tags
        ]
    
    def to_representation(self, instance):
        """조회 시 암호화된 내용을 복호화하여 반환"""
        data = super().to_representation(instance)
        data['content'] = instance.decrypt_content()
        return data
    
    def create(self, validated_data):
        """생성 시 내용 암호화 + 감정 분석 + 태그 연결"""
        tag_ids = validated_data.pop('tag_ids', [])
        plain_content = validated_data.pop('content', '')
        instance = Diary(**validated_data)
        instance.encrypt_content(plain_content)
        instance.save()
        
        # 태그 연결
        self._update_tags(instance, tag_ids)
        
        # 비동기로 감정 분석 (또는 동기로 바로 실행)
        try:
            from .emotion_service import analyze_diary_emotion
            analyze_diary_emotion(instance)
        except Exception as e:
            import logging
            logging.getLogger('diary').error(f"Emotion analysis failed: {e}")
        
        return instance
    
    def update(self, instance, validated_data):
        """수정 시 내용 암호화 + 감정 재분석 + 태그 업데이트"""
        tag_ids = validated_data.pop('tag_ids', None)
        content_changed = False
        
        if 'content' in validated_data:
            plain_content = validated_data.pop('content')
            instance.encrypt_content(plain_content)
            content_changed = True
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # 태그 업데이트 (tag_ids가 전달된 경우에만)
        if tag_ids is not None:
            self._update_tags(instance, tag_ids)
        
        # 내용이 변경되면 감정 재분석
        if content_changed:
            try:
                from .emotion_service import analyze_diary_emotion
                analyze_diary_emotion(instance)
            except Exception as e:
                import logging
                logging.getLogger('diary').error(f"Emotion analysis failed: {e}")
        
        return instance
    
    def _update_tags(self, diary, tag_ids):
        """일기의 태그를 업데이트"""
        # 기존 태그 연결 삭제
        DiaryTag.objects.filter(diary=diary).delete()
        
        # 새 태그 연결
        user = diary.user
        for tag_id in tag_ids:
            try:
                tag = Tag.objects.get(id=tag_id, user=user)
                DiaryTag.objects.create(diary=diary, tag=tag)
            except Tag.DoesNotExist:
                pass  # 잘못된 태그 ID는 무시


class DiaryTemplateSerializer(serializers.ModelSerializer):
    """
    일기 템플릿 Serializer
    """
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_system = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = DiaryTemplate
        fields = [
            'id', 'name', 'emoji', 'description', 'content',
            'template_type', 'template_type_display',
            'category', 'category_display',
            'use_count', 'is_active',
            'is_system', 'is_owner',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['use_count', 'created_at', 'updated_at']
    
    def get_is_system(self, obj):
        """시스템 템플릿 여부"""
        return obj.template_type == 'system'
    
    def get_is_owner(self, obj):
        """현재 사용자가 소유자인지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def create(self, validated_data):
        """템플릿 생성 시 사용자 자동 할당"""
        validated_data['user'] = self.context['request'].user
        validated_data['template_type'] = 'user'  # 사용자가 생성하면 항상 user 타입
        return super().create(validated_data)
