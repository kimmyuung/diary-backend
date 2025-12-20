# 📔 감성 일기 (AI Emotion Diary)

> **당신의 하루를 AI가 듣고, 이해하고, 그림으로 그려줍니다.**

사용자가 작성(또는 말한) 일기를 AI가 분석하여 감정을 추출하고, 그날의 기분에 맞는 그림을 그려주는 스마트한 일기장입니다. 웹과 모바일(iOS/Android) 모두를 지원하며, 개인정보는 안전하게 암호화되어 저장됩니다.

![Project Banner](https://via.placeholder.com/1200x600?text=AI+Emotion+Diary) 
*(추후 실제 스크린샷으로 교체 예정)*

---

## ✨ 주요 기능

### 1. 🧠 AI 감정 분석 (Emotion Analysis)
- **GPT-4o-mini**를 활용하여 일기 내용에서 8가지 핵심 감정(행복, 슬픔, 화남, 불안, 평온, 신남, 피곤, 사랑)을 분석합니다.
- 단순한 키워드 매칭이 아닌, 문맥을 이해하여 정확한 감정을 파악합니다.

### 2. 🎨 AI 그림 생성 (Image Generation)
- **DALL-E 3**를 사용하여 일기 내용에 어울리는 감성적인 이미지를 자동으로 생성합니다.
- (무료: 주 3회 / 프리미엄: 무제한)

### 3. 🎙️ 음성 일기 (Voice to Text)
- **Whisper API**를 통해 말하는 대로 일기가 작성됩니다.
- 100개 이상의 언어를 지원하며, 높은 정확도로 텍스트 변환이 가능합니다.

### 4. 📊 감정 리포트 (Emotion Reports)
- **주간/월간 리포트**: 나의 감정 변화를 한눈에 볼 수 있는 통계와 그래프를 제공합니다.
- **인사이트**: "이번 주는 주로 행복한 감정을 느꼈네요!"와 같은 맞춤형 코멘트를 제공합니다.

### 5. 🔐 프라이버시 중심 (Privacy First)
- 모든 일기 내용은 **AES-256** 알고리즘으로 암호화되어 데이터베이스에 저장됩니다.
- 오직 본인만이 내용을 복호화하여 볼 수 있습니다.

### 6. 📱 크로스 플랫폼 (Cross-Platform)
- **React Native (Expo)** 기반으로 웹, iOS, Android 어디서든 완벽하게 동작합니다.
- 반응형 디자인으로 모든 기기에서 최적화된 화면을 제공합니다.

---

## 🛠️ 기술 스택 (Tech Stack)

| 구분 | 기술 | 설명 |
|------|------|------|
| **Frontend** | React Native (Expo) | 크로스 플랫폼 앱 개발 |
| | TypeScript | 정적 타입 지원으로 안정성 확보 |
| | Expo Router | 파일 기반 라우팅 |
| | Axios | API 통신 |
| **Backend** | Django 5.1 | 강력한 Python 웹 프레임워크 |
| | Django REST Framework | RESTful API 구축 |
| | SQLite / PostgreSQL | 데이터베이스 (개발/배포) |
| **AI Models** | GPT-4o-mini | 고성능/저비용 감정 분석 |
| | DALL-E 3 | 고품질 이미지 생성 |
| | Whisper-1 | 음성 인식 (STT) |
| **Security** | AES Encryption | 데이터 암호화 (Django Cryptography) |
| | JWT | 안전한 사용자 인증 |

---

## 🚀 시작하기 (Getting Started)

이 프로젝트는 `backend`와 `frontend` 두 개의 모듈로 구성되어 있습니다.

### 사전 요구사항 (Prerequisites)
- Node.js (v18 이상)
- Python (3.12 이상)
- OpenAI API Key

### 1. 저장소 클론
```bash
git clone https://github.com/kimmyuung/diary-backend.git
cd diary-backend
```

### 2. Backend 설정 (Server)
```bash
cd backend

# 가상환경 생성 및 실행
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# .env 설정 (루트 디렉토리)
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 및 SECRET_KEY 입력

# DB 마이그레이션 및 실행
python manage.py migrate
python manage.py runserver
```
서버는 `http://localhost:8000`에서 실행됩니다.

### 3. Frontend 설정 (App/Web)
```bash
cd frontend

# 의존성 설치
npm install

# .env 설정
# .env 파일에 API_URL=http://localhost:8000 설정

# 앱 실행 (Web)
npm run web

# 앱 실행 (iOS/Android)
npm run ios
npm run android
```
웹은 `http://localhost:8081`에서 실행됩니다.

---

## 📡 주요 API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| **POST** | `/api/token/` | 로그인 (JWT 발급) |
| **GET** | `/api/diaries/` | 일기 목록 조회 |
| **POST** | `/api/diaries/` | 일기 작성 (자동 감정 분석) |
| **POST** | `/api/transcribe/` | 음성 파일을 텍스트로 변환 |
| **GET** | `/api/diaries/report/` | 주간/월간 감정 리포트 |
| **POST** | `/api/diaries/{id}/generate-image/` | AI 이미지 생성 |

---

## 📊 개발 로드맵 (Roadmap)

- [x] **Phase 1: MVP** (일기 CRUD, 기본 감정 분석)
- [x] **Phase 2: AI 고도화** (GPT-4o-mini, DALL-E 3, Whisper 적용)
- [x] **Phase 3: 사용자 경험 개선** (리포트 화면, 음성 입력, SNS 스타일 UI)
- [x] **Phase 4: 웹/앱 호환성** (SecureStore/localStorage 분기 처리)
- [ ] **Phase 5: 배포 및 운영** (Docker, AWS EC2, CI/CD)

---

## 📝 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
