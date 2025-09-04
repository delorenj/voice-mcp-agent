#!/bin/bash
# 🚨 EMERGENCY SSL CERTIFICATE RECOVERY SCRIPT 🚨
# This script fixes Traefik SSL certificate generation failures
# Created by your DevOps SSL Shaman

set -e

echo "🚨 EMERGENCY SSL CERTIFICATE RECOVERY INITIATED 🚨"
echo "======================================================="

# Colors for dramatic effect
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Starting emergency SSL certificate recovery..."

# Step 1: Stop Traefik if running
print_status "Stopping Traefik container..."
cd /home/delorenj/docker/trunk-main/core/traefik
docker compose down || true
print_success "Traefik stopped"

# Step 2: Clear corrupted ACME certificates
print_status "Clearing corrupted ACME certificates..."
if [ -f "traefik-data/acme.json" ]; then
    cp traefik-data/acme.json traefik-data/acme.json.backup.$(date +%Y%m%d_%H%M%S)
    print_warning "Backed up existing ACME file"
fi

echo '{}' > traefik-data/acme.json
chmod 600 traefik-data/acme.json
print_success "Fresh ACME file created with correct permissions"

# Step 3: Verify Cloudflare API token
print_status "Testing Cloudflare API connection..."
if command -v curl >/dev/null 2>&1; then
    API_TOKEN=$(grep CLOUDFLARE_DNS_API_TOKEN .env | cut -d'=' -f2)
    if [ ! -z "$API_TOKEN" ]; then
        RESPONSE=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
            -H "Authorization: Bearer $API_TOKEN" \
            -H "Content-Type: application/json")
        
        if echo "$RESPONSE" | grep -q '"success":true'; then
            print_success "Cloudflare API token is valid!"
        else
            print_error "Cloudflare API token validation failed!"
            print_error "Response: $RESPONSE"
            exit 1
        fi
    else
        print_error "No Cloudflare API token found in .env file"
        exit 1
    fi
else
    print_warning "curl not available, skipping API test"
fi

# Step 4: Start Traefik with new configuration
print_status "Starting Traefik with corrected SSL configuration..."
docker compose up -d
print_success "Traefik started successfully"

# Step 5: Wait for container to be ready
print_status "Waiting for Traefik to initialize..."
sleep 10

# Step 6: Check if Traefik is running
if docker compose ps | grep -q traefik; then
    print_success "Traefik container is running"
else
    print_error "Traefik container failed to start!"
    docker compose logs traefik | tail -20
    exit 1
fi

# Step 7: Monitor certificate generation
print_status "Monitoring certificate generation (this may take a few minutes)..."
print_status "Watching ACME logs for certificate generation..."

timeout 300 docker compose logs -f traefik 2>&1 | while IFS= read -r line; do
    echo "$line"
    if echo "$line" | grep -q "successfully obtained certificate"; then
        print_success "Certificate successfully obtained!"
        break
    fi
    if echo "$line" | grep -q "unable to obtain ACME certificate"; then
        print_error "Certificate generation failed!"
        break
    fi
done &

# Step 8: Test SSL endpoints after a delay
sleep 30
print_status "Testing SSL endpoints..."

# Test domains that should have certificates
DOMAINS=("lk.delo.sh" "lk-whip.delo.sh" "lk-turn.delo.sh")

for domain in "${DOMAINS[@]}"; do
    print_status "Testing $domain..."
    
    if timeout 10 curl -s -I "https://$domain" >/dev/null 2>&1; then
        print_success "$domain - SSL certificate working!"
    else
        print_warning "$domain - SSL certificate not yet ready (this is normal, may take a few minutes)"
    fi
done

print_status "Emergency SSL recovery script completed!"
print_status "Monitor Traefik logs with: docker compose -f /home/delorenj/docker/trunk-main/core/traefik/compose.yml logs -f traefik"
print_status "Check certificate status in traefik-data/acme.json after a few minutes"

echo "============================================================="
echo "🎉 SSL EMERGENCY RECOVERY COMPLETE! 🎉"
echo "============================================================="
echo "If certificates are still not generating, check:"
echo "1. Cloudflare API token permissions (Zone:Zone:Read, Zone:DNS:Edit)"
echo "2. Domain DNS is pointing to Cloudflare"
echo "3. No rate limiting is active (wait 1 hour if rate limited)"
echo "============================================================="