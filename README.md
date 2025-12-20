#  AI 기반 감성 일기 앱

사용자가 작성한 일기를 AI가 자동으로 분석하고, 감정을 시각화하며, 맞춤형 피드백을 제공하는 개인화된 일기 애플리케이션입니다.

## 🌟 주요 기능

- **AI 일기 작성**: 사용자 입력을 AI가 감성적인 일기로 변환
- **감정 분석**: 일기 내용에서 감정을 추출하고 시각화
- **이미지 생성**: DALL-E를 활용한 일기 맞춤형 이미지 생성
- **음성 입력**: Whisper API를 통한 음성-텍스트 변환
- **프라이버시 보호**: 암호화된 데이터 저장

## 🏗️ 시스템 아키텍처

### Frontend
- **React Native (Expo)** - 크로스 플랫폼 모바일 앱
- **TypeScript** - 타입 안정성
- **Axios** - API 통신

### Backend
- **Django 4.x** - 웹 프레임워크
- **Django REST Framework** - RESTful API
- **Celery + Redis** - 비동기 AI 처리
- **PostgreSQL** - 배포용 데이터베이스

### AI Services
- **OpenAI GPT-4** - 일기 작성 및 감성 분석
- **Whisper** - 음성-텍스트 변환
- **DALL-E 3** - 이미지 생성

## 📁 프로젝트 구조
diary-backend/
├── config/              # Django 설정
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── diary/              # 메인 앱
│   ├── models.py       # 데이터 모델
│   ├── views.py        # API 뷰
│   ├── serializers.py  # 직렬화
│   ├── ai_service.py   # AI 로직
│   └── tests/          # 테스트 코드
├── venv/               # 가상 환경
├── manage.py
└── requirements.txt

## 🚀 시작하기

### 1. 저장소 클론
```bash
git clone https://github.com/kimmyuung/diary-backend.git
cd diary-backend
```

### 2. 가상 환경 설정

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일 생성:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
OPENAI_API_KEY=your-openai-api-key
```

### 5. 데이터베이스 마이그레이션
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. 개발 서버 실행
```bash
python manage.py runserver
```

서버가 `http://127.0.0.1:8000/`에서 실행됩니다.

## 🧪 테스트 실행
```bash
# 모든 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test diary

# 커버리지 포함
coverage run --source='.' manage.py test
coverage report
```

## 📡 API 엔드포인트

### 인증
- `POST /api/token/` - JWT 토큰 발급
- `POST /api/token/refresh/` - 토큰 갱신

### 일기
- `GET /api/diaries/` - 일기 목록
- `POST /api/diaries/` - 일기 작성
- `GET /api/diaries/{id}/` - 일기 상세
- `PUT /api/diaries/{id}/` - 일기 수정
- `DELETE /api/diaries/{id}/` - 일기 삭제

### AI 기능
- `POST /api/diaries/{id}/generate-image/` - 이미지 생성
- `POST /api/analyze/` - 감정 분석
- `POST /api/transcribe/` - 음성-텍스트 변환

## 🛠️ 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **Backend** | Django 4.2, Django REST Framework |
| **Database** | SQLite3 (개발), PostgreSQL (배포) |
| **AI/ML** | OpenAI API (GPT-4, Whisper, DALL-E) |
| **캐싱** | Redis |
| **비동기 처리** | Celery |
| **인증** | JWT (Simple JWT) |
| **배포** | Gunicorn, Nginx, Docker |

## 📊 개발 로드맵

### ✅ Phase 1 - MVP (완료)
- [x] Django 백엔드 구축
- [x] RESTful API 구현
- [x] 기본 CRUD 기능
- [x] 감성 분석 기능

### 🔄 Phase 2 - AI 고도화 (진행 중)
- [ ] 이미지 생성 (DALL-E 3)
- [ ] 감정 그래프 시각화
- [ ] AI 피드백 개선

### 📅 Phase 3 - 추가 기능
- [ ] 음성 입력
- [ ] 실시간 알림 (WebSocket)
- [ ] 프리미엄 구독 시스템

### 🚀 Phase 4 - 배포
- [ ] Docker 컨테이너화
- [ ] AWS 배포
- [ ] CI/CD 파이프라인

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일 참조

## 👥 팀

- **Backend Developer** - [kimmyuung](https://github.com/kimmyuung)

## 📞 문의

프로젝트 관련 문의: [GitHub Issues](https://github.com/kimmyuung/diary-backend/issues)

---

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!
