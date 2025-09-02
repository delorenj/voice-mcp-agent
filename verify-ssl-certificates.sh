#!/bin/bash

# 🚨 LIVEKIT SSL CERTIFICATE VERIFICATION SCRIPT 🚨
# This script verifies and monitors SSL certificate status for all LiveKit domains

set -e

echo "🚨 SSL CERTIFICATE VERIFICATION STARTING 🚨"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# LiveKit domains to check
DOMAINS=("lk.delo.sh" "lk-whip.delo.sh" "lk-turn.delo.sh")

# Function to check certificate status
check_certificate() {
    local domain=$1
    echo -e "${BLUE}🔍 Checking certificate for $domain...${NC}"
    
    # Check if domain resolves
    if ! nslookup "$domain" >/dev/null 2>&1; then
        echo -e "${RED}❌ Domain $domain does not resolve${NC}"
        return 1
    fi
    
    # Check SSL certificate
    if curl -sSf --connect-timeout 10 -I "https://$domain" >/dev/null 2>&1; then
        # Get certificate info
        cert_info=$(openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null </dev/null | openssl x509 -noout -dates 2>/dev/null)
        if [ $? -eq 0 ] && echo "$cert_info" | grep -q "notAfter"; then
            expiry=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
            echo -e "${GREEN}✅ $domain has valid SSL certificate (expires: $expiry)${NC}"
            return 0
        fi
    fi
    
    # Check if it's a self-signed certificate
    if openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null </dev/null | openssl x509 -noout -issuer 2>/dev/null | grep -qi "self"; then
        echo -e "${YELLOW}⚠️ $domain has SELF-SIGNED certificate (needs proper Let's Encrypt cert)${NC}"
        return 2
    fi
    
    echo -e "${RED}❌ $domain SSL certificate check failed${NC}"
    return 1
}

# Function to check Traefik ACME status
check_acme_status() {
    echo -e "${BLUE}🔍 Checking Traefik ACME certificate status...${NC}"
    
    if [ -f "/home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json" ]; then
        # Count certificates in ACME storage
        cert_count=$(jq -r '.letsencrypt.Certificates | length' /home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json 2>/dev/null || echo "0")
        echo -e "${BLUE}📋 ACME storage contains $cert_count certificates${NC}"
        
        if [ "$cert_count" -gt 0 ]; then
            # List certificate domains
            echo -e "${BLUE}📋 Certificate domains in ACME storage:${NC}"
            jq -r '.letsencrypt.Certificates[].domain.main' /home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json 2>/dev/null | while read domain; do
                echo -e "   - ${GREEN}$domain${NC}"
            done
        fi
    else
        echo -e "${YELLOW}⚠️ ACME storage file not found${NC}"
    fi
}

# Function to monitor certificate generation
monitor_certificate_generation() {
    echo -e "${BLUE}🔍 Monitoring Traefik logs for certificate generation...${NC}"
    
    # Get recent Traefik logs related to certificates
    echo -e "${BLUE}Recent Traefik certificate activity:${NC}"
    docker logs traefik --since 5m 2>&1 | grep -i "certificate\|acme\|letsencrypt\|cloudflare" | tail -10 | while read line; do
        if echo "$line" | grep -qi "error"; then
            echo -e "${RED}❌ $line${NC}"
        elif echo "$line" | grep -qi "success\|obtained\|issued"; then
            echo -e "${GREEN}✅ $line${NC}"
        else
            echo -e "${YELLOW}📋 $line${NC}"
        fi
    done
}

# Function to test WebRTC connectivity
test_webrtc_connectivity() {
    echo -e "${BLUE}🔍 Testing WebRTC connectivity...${NC}"
    
    # Test LiveKit server health endpoint
    if curl -sSf --connect-timeout 10 "https://lk.delo.sh/rtc/validate" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ LiveKit server health check passed${NC}"
    else
        echo -e "${YELLOW}⚠️ LiveKit server health check failed - server may still be starting${NC}"
    fi
    
    # Test TURN server TLS
    echo -e "${BLUE}🔍 Testing TURN server TLS on port 5349...${NC}"
    if timeout 5 openssl s_client -connect lk-turn.delo.sh:5349 -servername lk-turn.delo.sh </dev/null 2>/dev/null | grep -q "CONNECTED"; then
        echo -e "${GREEN}✅ TURN server TLS connection successful${NC}"
    else
        echo -e "${YELLOW}⚠️ TURN server TLS connection failed${NC}"
    fi
}

# Function to force certificate renewal
force_certificate_renewal() {
    echo -e "${BLUE}🔧 Forcing certificate renewal for domains with issues...${NC}"
    
    # Clear ACME cache to force renewal
    echo '{"letsencrypt": {"Account": {"Email": "delorenj@delo.sh", "Registration": {"body": {"status": "valid"}, "uri": "https://acme-v02.api.letsencrypt.org/acme/acct/2634568177"}, "PrivateKey": "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", "KeyType": "4096"}, "Certificates": null}}' > /home/delorenj/docker/trunk-main/core/traefik/traefik-data/acme.json
    
    # Restart Traefik to trigger fresh certificate requests
    echo -e "${YELLOW}Restarting Traefik to trigger certificate renewal...${NC}"
    cd /home/delorenj/docker/trunk-main/core/traefik
    docker compose restart traefik
    
    echo -e "${GREEN}✅ Certificate renewal initiated${NC}"
}

# Main execution
echo "========================================="
echo -e "${BLUE}🔍 STEP 1: Checking current certificate status${NC}"
echo "========================================="

certificate_issues=0
for domain in "${DOMAINS[@]}"; do
    if ! check_certificate "$domain"; then
        ((certificate_issues++))
    fi
done

echo ""
echo "========================================="
echo -e "${BLUE}🔍 STEP 2: Checking Traefik ACME status${NC}"
echo "========================================="

check_acme_status

echo ""
echo "========================================="
echo -e "${BLUE}🔍 STEP 3: Monitoring certificate generation${NC}"
echo "========================================="

monitor_certificate_generation

echo ""
echo "========================================="
echo -e "${BLUE}🔍 STEP 4: Testing WebRTC connectivity${NC}"
echo "========================================="

test_webrtc_connectivity

echo ""
echo "========================================="
echo -e "${BLUE}📋 SUMMARY REPORT${NC}"
echo "========================================="

if [ $certificate_issues -eq 0 ]; then
    echo -e "${GREEN}🎉 SUCCESS! All LiveKit domains have valid SSL certificates!${NC}"
    echo -e "${GREEN}🚀 WebRTC should work properly with secure connections${NC}"
else
    echo -e "${YELLOW}⚠️ $certificate_issues domain(s) have certificate issues${NC}"
    echo -e "${BLUE}Certificate generation may still be in progress...${NC}"
    
    echo ""
    echo -e "${BLUE}🔧 Would you like to force certificate renewal? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        force_certificate_renewal
        echo ""
        echo -e "${BLUE}Please wait 2-3 minutes and run this script again to check certificate status.${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "- Check Traefik logs: docker logs traefik --tail 50"
echo "- Check LiveKit logs: docker logs livekit-server --tail 20"
echo "- Test SSL manually: curl -I https://lk.delo.sh"
echo "- Monitor certificates: watch 'curl -I https://lk.delo.sh 2>&1 | head -5'"

echo ""
echo "🚨 SSL CERTIFICATE VERIFICATION COMPLETE 🚨"
EOF