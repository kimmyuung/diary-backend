#!/bin/bash
# =============================================================================
# nginx.conf에서 SSL/HTTPS 설정을 활성화하는 스크립트
#
# SSL 인증서 발급 후에만 실행하세요! (setup-ssl.sh 먼저 실행)
# =============================================================================

set -e

SCRIPT_DIR="$(dirname "$0")"
NGINX_CONF="$SCRIPT_DIR/../nginx/nginx.conf"

echo "🔒 HTTPS 활성화 중..."

# 1. HTTP 리다이렉트 활성화
# 주석된 리다이렉트 블록 활성화
sed -i 's/# location \/ {$/location \/ {/' "$NGINX_CONF"
sed -i 's/#     return 301 https/    return 301 https/' "$NGINX_CONF"
sed -i 's/# }$/}/' "$NGINX_CONF"

# 2. HTTPS 서버 블록 주석 해제 (# server { ... } 전체)
# 이 부분은 복잡하므로 수동으로 해제하는 것을 권장

echo ""
echo "⚠️  수동 작업 필요:"
echo "   nginx.conf에서 HTTPS 서버 블록(110~180행)의 주석(#)을 해제하세요."
echo ""
echo "   편집 파일: $NGINX_CONF"
echo ""
echo "   주석 해제 후:"
echo "   docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload"
echo ""
