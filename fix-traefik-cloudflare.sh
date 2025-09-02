#!/bin/bash

# 🚨 TRAEFIK CLOUDFLARE API FIX 🚨
# This script fixes the Cloudflare API authentication issues causing SSL failures

set -e

echo "🚨 TRAEFIK CLOUDFLARE API EMERGENCY FIX 🚨"
echo "Fixing the root cause of SSL certificate failures..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load secrets
source /home/delorenj/.config/zshyzsh/secrets.zsh

echo -e "${BLUE}🔍 Checking current Cloudflare configuration...${NC}"

# Check if we have the new API token format
if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
    echo -e "${GREEN}✅ Found CLOUDFLARE_API_TOKEN${NC}"
    USE_TOKEN=true
else
    echo -e "${YELLOW}⚠️ No CLOUDFLARE_API_TOKEN found, checking for legacy API key...${NC}"
    if [ -n "$CLOUDFLARE_API_KEY" ]; then
        echo -e "${GREEN}✅ Found CLOUDFLARE_API_KEY (legacy)${NC}"
        USE_TOKEN=false
    else
        echo -e "${RED}❌ No Cloudflare credentials found!${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}🔧 Updating Traefik configuration for proper Cloudflare DNS challenge...${NC}"

# Navigate to Traefik directory
cd /home/delorenj/docker/trunk-main/core/traefik

# Create backup of current configuration
cp traefik-data/traefik.yml traefik-data/traefik.yml.backup.$(date +%s)

# Update traefik.yml with proper configuration
cat > traefik-data/traefik.yml << 'EOF'
api:
  dashboard: true
  debug: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: delorenj@delo.sh
      storage: /etc/traefik/acme.json
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
        delayBeforeCheck: 60s
      # Use Let's Encrypt production server
      caServer: "https://acme-v02.api.letsencrypt.org/directory"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: proxy
    watch: true
    useBindPortIP: false

  file:
    directory: "/dynamic"

# Enable metrics for monitoring
metrics:
  prometheus: true

# Configure logging
log:
  level: INFO

# Access logs for debugging
accessLog: {}
EOF

echo -e "${GREEN}✅ Updated traefik.yml with proper DNS challenge configuration${NC}"

# Update compose file with correct environment variables
echo -e "${BLUE}🔧 Updating Traefik compose file for proper Cloudflare authentication...${NC}"

# Create backup of compose file
cp compose.yml compose.yml.backup.$(date +%s)

if [ "$USE_TOKEN" = true ]; then
    # Use new API token method
    cat > compose.yml << EOF
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
      # NEW Cloudflare DNS API Token method (PREFERRED)
      - CLOUDFLARE_DNS_API_TOKEN=$CLOUDFLARE_API_TOKEN
      - CLOUDFLARE_EMAIL=delorenj@delo.sh
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
else
    # Use legacy API key method
    cat > compose.yml << EOF
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
      # Legacy Cloudflare Global API Key method (FALLBACK)
      - CF_API_EMAIL=delorenj@delo.sh
      - CF_API_KEY=$CLOUDFLARE_API_KEY
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
fi

echo -e "${GREEN}✅ Updated Traefik compose file with proper Cloudflare authentication${NC}"

echo -e "${BLUE}🔧 Clearing old ACME data and restarting Traefik...${NC}"

# Clear old ACME data to force fresh certificate requests
echo "{}" > traefik-data/acme.json
chmod 600 traefik-data/acme.json

# Restart Traefik with new configuration
echo "Stopping Traefik..."
docker compose down traefik

echo "Starting Traefik with fixed configuration..."
docker compose up -d traefik

echo -e "${GREEN}✅ Traefik restarted with fixed Cloudflare configuration${NC}"

echo -e "${BLUE}🔍 Monitoring certificate generation...${NC}"
echo "This may take 1-2 minutes for DNS propagation..."

# Wait for Traefik to start
sleep 10

# Monitor logs for certificate generation
echo "Checking Traefik logs for certificate generation..."
timeout 60 docker logs -f traefik 2>&1 | grep -i "certificate\|acme\|cloudflare" || true

echo ""
echo -e "${GREEN}🎉 Cloudflare API fix applied!${NC}"
echo -e "${YELLOW}Certificates should now generate properly for all LiveKit domains.${NC}"

echo ""
echo -e "${BLUE}Next: Run the main SSL fix script:${NC}"
echo "cd /home/delorenj/code/mcp/voice-mcp-agent"
echo "./EMERGENCY-SSL-FIX.sh"

echo ""
echo "🚨 TRAEFIK CLOUDFLARE API FIX COMPLETE 🚨"
EOF