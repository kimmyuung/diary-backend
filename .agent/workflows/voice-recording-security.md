---
description: 음성 녹음으로 일기 작성 및 보안 정책 적용 방법
---

# 음성 녹음 일기 작성 + 보안 정책

## 1. 음성 녹음 → 텍스트 변환

### 필요 패키지 설치
```bash
cd frontend
npx expo install expo-av expo-file-system
```

### 사용 흐름
1. 녹음 버튼 클릭 → 음성 녹음 시작
2. 5초 간격으로 청크 → Whisper API → 텍스트 변환
3. 실시간 화면 업데이트
4. 일시정지/종료 버튼으로 제어

## 2. 저장 전 승인 프로세스

1. 저장 버튼 클릭
2. 미리보기 모달 표시
3. 사용자 확인 → 저장

## 3. 보안 정책

| 레이어 | 방법 |
|--------|------|
| 전송 | HTTPS/TLS |
| 서버 저장 | AES-256 암호화 |
| 앱 저장 | SecureStore |
| 인증 | JWT + Refresh Token |

### 암호화 키 설정
```bash
# .env.production
DIARY_ENCRYPTION_KEY=your-32-byte-fernet-key
```

> ⚠️ 암호화 키 분실 시 일기 복구 불가능!
