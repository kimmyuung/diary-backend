#!/bin/bash
# =============================================================================
# AWS EC2 초기 설정 스크립트
# Ubuntu 22.04 LTS 기준
# =============================================================================

set -e

echo "🚀 EC2 초기 설정을 시작합니다..."

# =============================================================================
# 1. 시스템 업데이트
# =============================================================================
echo "📦 시스템 패키지 업데이트 중..."
sudo apt-get update
sudo apt-get upgrade -y

# =============================================================================
# 2. Docker 설치
# =============================================================================
echo "🐳 Docker 설치 중..."

# 필요한 패키지 설치
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Docker GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

echo "✅ Docker 설치 완료"

# =============================================================================
# 3. Docker Compose 설치
# =============================================================================
echo "🐳 Docker Compose 설치 중..."

sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "✅ Docker Compose 설치 완료: $(docker-compose --version)"

# =============================================================================
# 4. 방화벽 설정
# =============================================================================
echo "🔥 방화벽 설정 중..."

sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable

echo "✅ 방화벽 설정 완료"

# =============================================================================
# 5. Certbot 설치 (Let's Encrypt)
# =============================================================================
echo "🔐 Certbot 설치 중..."

sudo apt-get install -y certbot python3-certbot-nginx

echo "✅ Certbot 설치 완료"

# =============================================================================
# 5. 앱 디렉토리 생성
# =============================================================================
echo "📁 앱 디렉토리 생성 중..."

mkdir -p ~/app
mkdir -p ~/app/nginx/ssl

echo "✅ 디렉토리 생성 완료"

# =============================================================================
# 6. Swap 메모리 설정 (t2.micro 등 작은 인스턴스용)
# =============================================================================
echo "💾 Swap 메모리 설정 중..."

if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✅ Swap 메모리 2GB 설정 완료"
else
    echo "ℹ️ Swap 이미 설정됨"
fi

# =============================================================================
# 완료
# =============================================================================
echo ""
echo "============================================="
echo "✅ EC2 초기 설정이 완료되었습니다!"
echo "============================================="
echo ""
echo "다음 단계:"
echo "1. 로그아웃 후 다시 로그인 (docker 그룹 적용)"
echo "2. ~/app 디렉토리에 소스 코드 복사"
echo "3. .env.production 파일 생성 및 설정"
echo "4. ./scripts/deploy.sh 실행"
echo ""
echo "🔐 SSL 인증서 설정 (Let's Encrypt):"
echo "   도메인 준비 후 아래 명령어 실행:"
echo "   ./scripts/setup-ssl.sh your-domain.com your-email@example.com"
echo ""

