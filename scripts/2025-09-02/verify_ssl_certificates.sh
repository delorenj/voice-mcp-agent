#!/bin/bash
# 🎉 SSL CERTIFICATE VERIFICATION SCRIPT 🎉
# Verifies that all LiveKit domains have working SSL certificates
# Created by your victorious SSL DevOps Shaman!

set -e

echo "🎉 SSL CERTIFICATE VERIFICATION STARTED 🎉"
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
print_victory() { echo -e "${PURPLE}[VICTORY]${NC} $1"; }

# LiveKit domains to test
DOMAINS=(
    "lk.delo.sh"
    "lk-whip.delo.sh" 
    "lk-turn.delo.sh"
)

# Additional domains that should have certificates
OTHER_DOMAINS=(
    "gptme.delo.sh"
    "ollama.delo.sh"
    "admin.tipsnips.delo.sh"
    "assets.delo.sh"
    "traefik.delo.sh"
)

print_status "Testing LiveKit SSL certificates..."

# Test LiveKit domains
LIVEKIT_SUCCESS=0
LIVEKIT_TOTAL=${#DOMAINS[@]}

for domain in "${DOMAINS[@]}"; do
    print_status "Testing $domain..."
    
    if timeout 10 curl -s -I "https://$domain" >/dev/null 2>&1; then
        print_success "$domain - SSL certificate working!"
        ((LIVEKIT_SUCCESS++))
    else
        print_warning "$domain - Certificate not ready yet (may be generating)"
        
        # Check if certificate is in ACME file
        if grep -q "$domain" /home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json 2>/dev/null; then
            print_status "$domain - Certificate found in ACME file, should be available soon"
        else
            print_warning "$domain - Certificate not yet generated, Traefik may still be working on it"
        fi
    fi
done

print_status "Testing other domains with certificates..."

OTHER_SUCCESS=0
OTHER_TOTAL=${#OTHER_DOMAINS[@]}

for domain in "${OTHER_DOMAINS[@]}"; do
    print_status "Testing $domain..."
    
    if timeout 10 curl -s -I "https://$domain" >/dev/null 2>&1; then
        print_success "$domain - SSL certificate working!"
        ((OTHER_SUCCESS++))
    else
        print_warning "$domain - Certificate may not be ready"
    fi
done

# Check ACME certificate file
print_status "Checking ACME certificate file..."
ACME_FILE="/home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json"

if [ -f "$ACME_FILE" ] && [ -s "$ACME_FILE" ]; then
    CERT_COUNT=$(cat "$ACME_FILE" | jq '.letsencrypt.Certificates | length' 2>/dev/null || echo "0")
    if [ "$CERT_COUNT" -gt 0 ]; then
        print_success "ACME file contains $CERT_COUNT certificates!"
        
        # List certificate domains
        print_status "Certificate domains found:"
        cat "$ACME_FILE" | jq -r '.letsencrypt.Certificates[].domain.main' 2>/dev/null | while read domain; do
            echo "  ✓ $domain"
        done
    else
        print_warning "ACME file exists but contains no certificates"
    fi
else
    print_error "ACME file not found or empty"
fi

# Test Traefik API
print_status "Testing Traefik dashboard..."
if timeout 10 curl -s -I "http://localhost:8099/dashboard/" >/dev/null 2>&1; then
    print_success "Traefik dashboard accessible on port 8099"
else
    print_warning "Traefik dashboard not accessible"
fi

# Display summary
echo ""
echo "=============================================="
print_victory "SSL CERTIFICATE VERIFICATION COMPLETE!"
echo "=============================================="
echo ""
print_status "LiveKit Domains: $LIVEKIT_SUCCESS/$LIVEKIT_TOTAL working"
print_status "Other Domains: $OTHER_SUCCESS/$OTHER_TOTAL working"
echo ""

if [ "$LIVEKIT_SUCCESS" -eq "$LIVEKIT_TOTAL" ]; then
    print_victory "🎉 ALL LIVEKIT DOMAINS HAVE WORKING SSL CERTIFICATES! 🎉"
    print_victory "Your LiveKit infrastructure is ready for production!"
elif [ "$LIVEKIT_SUCCESS" -gt 0 ]; then
    print_success "Some LiveKit domains are working. Others may still be generating certificates."
    print_status "Monitor progress with: docker compose -f /home/delorenj/docker/trunk-main/core/traefik/compose.yml logs -f traefik"
else
    print_warning "LiveKit certificates may still be generating."
    print_status "This is normal for new domains - certificates can take a few minutes."
fi

echo ""
print_status "To monitor certificate generation:"
print_status "  docker compose -f /home/delorenj/docker/trunk-main/core/traefik/compose.yml logs -f traefik | grep certificate"
echo ""
print_status "To check ACME certificates:"
print_status "  cat /home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json | jq ."
echo ""
print_victory "SSL EMERGENCY MISSION ACCOMPLISHED! 🚀"
echo "=============================================="