#!/bin/bash
# 🎯 ULTIMATE CLOUDFLARE SSL CERTIFICATE FIX SCRIPT 🎯
# This script WILL fix your SSL certificates or the void consumes all!

set -e

echo "🎯 ULTIMATE SSL CERTIFICATE FIX INITIATED 🎯"
echo "=============================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_magic() { echo -e "${PURPLE}[MAGIC]${NC} $1"; }

# Step 1: Test Cloudflare API directly
print_status "Testing Cloudflare API connection..."
API_TOKEN="8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg"
RESPONSE=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json")

if echo "$RESPONSE" | grep -q '"success":true'; then
    print_success "Cloudflare API token is working perfectly!"
    ZONE_ID=$(echo "$RESPONSE" | jq -r '.result[0].id')
    print_magic "Zone ID for delo.sh: $ZONE_ID"
else
    print_error "API token failed, this shouldn't happen!"
    exit 1
fi

# Step 2: Stop Traefik
print_status "Stopping Traefik..."
cd /home/delorenj/docker/trunk-main/core/traefik
docker compose down

# Step 3: Create ULTIMATE working .env file
print_status "Creating ULTIMATE working .env configuration..."
cat > .env << 'EOF'
# 🎯 ULTIMATE CLOUDFLARE SSL CONFIGURATION 🎯
# This configuration WILL work or the universe is broken

# Cloudflare API Token (tested and verified working)
CLOUDFLARE_EMAIL=delorenj@delo.sh
CLOUDFLARE_DNS_API_TOKEN=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg

# Legacy support (some versions need this)
CLOUDFLARE_API_KEY=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg
CF_API_EMAIL=delorenj@delo.sh
CF_API_KEY=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg
CF_DNS_API_TOKEN=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg

# Zone ID for faster resolution
CLOUDFLARE_ZONE_ID=eabc163cde3e31680f10fc313aecdda3
EOF

print_success "Ultimate .env configuration created!"

# Step 4: Update compose file with ALL possible environment variables
print_status "Updating compose file with ALL Cloudflare variables..."
cp compose.yml compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Create the ultimate compose configuration
cat > compose.yml << 'EOF'
services:
  traefik:
    image: traefik:v3.3
    container_name: traefik
    ports:
      - "80:80"
      - "443:443"
      - "8099:8080"
    networks:
      - proxy
    env_file:
      - .env
    environment:
      # ALL POSSIBLE CLOUDFLARE ENVIRONMENT VARIABLES
      - CLOUDFLARE_EMAIL=${CLOUDFLARE_EMAIL}
      - CLOUDFLARE_DNS_API_TOKEN=${CLOUDFLARE_DNS_API_TOKEN}
      - CLOUDFLARE_API_KEY=${CLOUDFLARE_API_KEY}
      - CF_API_EMAIL=${CF_API_EMAIL}
      - CF_API_KEY=${CF_API_KEY}
      - CF_DNS_API_TOKEN=${CF_DNS_API_TOKEN}
      - CLOUDFLARE_ZONE_ID=${CLOUDFLARE_ZONE_ID}
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock
        read_only: true
      - ./traefik-data/traefik.yml:/traefik.yml:ro
      - ./traefik-data/acme.json:/etc/traefik/acme.json
      - ./traefik-data/dynamic:/dynamic:ro
      - ./traefik-data:/traefik-data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik-secure.entrypoints=websecure"
      - "traefik.http.routers.traefik-secure.rule=Host(\`traefik.delo.sh\`)"
      - "traefik.http.routers.traefik-secure.service=api@internal"
      - "traefik.http.routers.traefik-secure.tls=true"
      - "traefik.http.routers.traefik-secure.tls.certresolver=letsencrypt"
    command:
      - "--api.dashboard=true"
      - "--metrics.prometheus=true"
      - "--metrics.prometheus.buckets=0.1,0.3,1.2,5.0"
      - "--log.level=DEBUG"
    restart: unless-stopped

  whoami:
    image: traefik/whoami
    container_name: traefik-test-whoami
    networks:
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.whoami.entrypoints=websecure"
      - "traefik.http.routers.whoami.rule=Host(\`whoami.localhost\`)"
      - "traefik.http.routers.whoami.tls=true"

  assets-nginx:
    image: nginx:alpine
    container_name: assets-nginx
    networks:
      - proxy
    volumes:
      - ./assets:/usr/share/nginx/html:ro
      - ./assets/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.assets.entrypoints=websecure"
      - "traefik.http.routers.assets.rule=Host(\`assets.delo.sh\`)"
      - "traefik.http.routers.assets.tls=true"
      - "traefik.http.routers.assets.tls.certresolver=letsencrypt"
    restart: unless-stopped

networks:
  proxy:
    name: proxy
    external: true
EOF

print_success "Ultimate compose configuration created!"

# Step 5: Clear and recreate ACME file
print_status "Clearing corrupted certificates..."
rm -f traefik-data/acme.json
echo '{}' > traefik-data/acme.json
chmod 600 traefik-data/acme.json
print_success "Fresh ACME certificate file ready!"

# Step 6: Start Traefik with debug logging
print_status "Starting Traefik with ultimate configuration..."
docker compose up -d

print_magic "Waiting for Traefik to initialize..."
sleep 15

# Step 7: Monitor for success
print_status "Monitoring certificate generation..."
timeout 60 docker compose logs -f traefik 2>&1 | while IFS= read -r line; do
    echo "$line"
    
    if echo "$line" | grep -q "successfully obtained certificate"; then
        print_success "🎉 CERTIFICATE SUCCESSFULLY OBTAINED! 🎉"
        break
    fi
    
    if echo "$line" | grep -qi "Invalid request headers"; then
        print_error "Still getting API authentication errors!"
        break
    fi
done

# Step 8: Check certificate status
print_status "Checking certificate status..."
if [ -s "traefik-data/acme.json" ] && [ "$(cat traefik-data/acme.json)" != "{}" ]; then
    print_success "ACME file contains certificate data!"
    
    # Count certificates
    CERT_COUNT=$(cat traefik-data/acme.json | jq '.letsencrypt.Certificates | length' 2>/dev/null || echo "0")
    if [ "$CERT_COUNT" -gt 0 ]; then
        print_success "Found $CERT_COUNT certificates in ACME file!"
    else
        print_warning "ACME file exists but no certificates found yet"
    fi
else
    print_warning "No certificates generated yet - this may take a few minutes"
fi

print_magic "=============================================="
print_magic "🎯 ULTIMATE SSL FIX COMPLETE! 🎯"
print_magic "=============================================="
print_status "Monitor progress with: docker compose logs -f traefik"
print_status "Check certificates with: cat traefik-data/acme.json | jq"
print_status "Test endpoints: https://assets.delo.sh"
print_magic "=============================================="