#!/bin/bash
# =============================================================================
# SSL 인증서 갱신 스크립트
# 
# Cron Job 또는 수동으로 실행 가능
# 인증서 갱신 후 nginx 컨테이너를 자동으로 리로드합니다.
# =============================================================================

set -e

SCRIPT_DIR="$(dirname "$0")"
SSL_DIR="$SCRIPT_DIR/../nginx/ssl"

echo "🔄 SSL 인증서 갱신 시도 중..."

# 인증서 갱신 시도
sudo certbot renew --quiet

# 갱신된 인증서가 있는지 확인
if [ -f /etc/letsencrypt/live/*/fullchain.pem ]; then
    DOMAIN=$(ls /etc/letsencrypt/live/ | grep -v README | head -1)
    
    if [ -n "$DOMAIN" ]; then
        echo "📋 갱신된 인증서 복사 중... ($DOMAIN)"
        
        sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$SSL_DIR/fullchain.pem"
        sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem "$SSL_DIR/privkey.pem"
        sudo chmod 644 "$SSL_DIR"/*.pem
        
        # nginx 리로드
        echo "🔄 nginx 리로드 중..."
        cd "$SCRIPT_DIR/.."
        docker-compose -f docker-compose.prod.yml exec -T nginx nginx -s reload 2>/dev/null || true
        
        echo "✅ SSL 인증서 갱신 완료"
    fi
else
    echo "ℹ️ 갱신할 인증서가 없습니다."
fi
