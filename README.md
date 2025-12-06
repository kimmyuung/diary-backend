# 📔 [CAPSTONE] AI 기반 감성 일기 분석 서버 (Diary-Backend)

## 🌟 프로젝트 개요

본 프로젝트는 React Native로 개발된 모바일 일기 앱의 **백엔드 시스템**으로, 사용자에게 REST API를 제공하고 핵심적인 **일기 감성 분석 및 AI 대화 처리**를 담당합니다. Django REST Framework를 기반으로 하며, AI 모델을 통합하여 실시간 분석 기능을 구현했습니다.

### 🔑 주요 기능
| 기능 | 설명 |
| :--- | :--- |
| **API 통신** | 사용자 인증, 일기 CRUD(작성, 조회, 수정, 삭제)를 위한 RESTful API 제공 |
| **감성 분석** | 사용자가 작성한 일기 텍스트를 기반으로 긍정/부정 감성을 분석 |
| **AI 피드백** | 분석된 감성 결과에 따라 사용자에게 맞춤형 피드백을 제공하는 AI 챗봇 기능 |
| **데이터 관리** | 일기 데이터 및 사용자 정보를 안전하게 관리하는 데이터베이스(DB) 연결 |

### 🛠️ 기술 스택 (Technology Stack)
* **Backend Framework:** Python 3.x, **Django (4.x)**
* **API:** **Django REST Framework (DRF)**
* **Database:** SQLite3 (개발 환경), PostgreSQL/MySQL (배포 시)
* **AI/ML:** **Custom AI Model Integration** (또는 OpenAI/Gemini API 등)
* **Deployment:** Gunicorn, Nginx (예시)
