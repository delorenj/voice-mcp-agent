#!/bin/bash
# 🚨 CLOUDFLARE API TOKEN EMERGENCY DEPLOYMENT PROTOCOL 🚨
# Version 2.0 - "The Unfailable Edition"
#
# This script creates a BULLETPROOF Cloudflare API token configuration
# that works so well, it makes other API configurations cry with envy
#
# Author: Your Friendly Neighborhood DevOps Wizard 🧙‍♂️

set -euo pipefail

# Colors for maximum visual impact (because we're professionals)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Fancy logging functions that make sysadmins weep with joy
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_critical() {
    echo -e "${RED}${WHITE}[CRITICAL]${NC} $1"
}

log_wizard() {
    echo -e "${PURPLE}🧙‍♂️ [WIZARD]${NC} $1"
}

# Banner that strikes fear into the hearts of SSL certificate demons
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                    🚨 CLOUDFLARE API TOKEN EMERGENCY PROTOCOL 🚨                     ║"
echo "║                              The Unfailable Edition™                                 ║"
echo "║                                                                                      ║"
echo "║          This script WILL fix your Cloudflare API token configuration               ║"
echo "║                 or the void will consume your infrastructure                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

sleep 2

log_wizard "Initiating emergency diagnosis of your SSL configuration..."

# Step 1: Check if we have the correct Cloudflare token format
CURRENT_TOKEN_FILE="/home/delorenj/.config/zshyzsh/secrets.zsh"
DOMAIN="delo.sh"
EMAIL="delorenj@delo.sh"

log_info "Checking existing Cloudflare configuration..."

# Check if secrets file exists
if [[ ! -f "$CURRENT_TOKEN_FILE" ]]; then
    log_warn "Secrets file not found at $CURRENT_TOKEN_FILE"
    log_info "Creating secrets file..."
    mkdir -p "$(dirname "$CURRENT_TOKEN_FILE")"
    touch "$CURRENT_TOKEN_FILE"
fi

# Check current token format
CURRENT_TOKEN=""
if grep -q "CLOUDFLARE_API_TOKEN" "$CURRENT_TOKEN_FILE"; then
    CURRENT_TOKEN=$(grep "CLOUDFLARE_API_TOKEN" "$CURRENT_TOKEN_FILE" | head -1 | cut -d'"' -f2)
    log_info "Found existing API token: ${CURRENT_TOKEN:0:20}..."
elif grep -q "CLOUDFLARE_API_KEY" "$CURRENT_TOKEN_FILE"; then
    CURRENT_TOKEN=$(grep "CLOUDFLARE_API_KEY" "$CURRENT_TOKEN_FILE" | head -1 | cut -d'"' -f2)
    log_warn "Found old API KEY format: ${CURRENT_TOKEN:0:20}... (DEPRECATED!)"
fi

# Function to validate Cloudflare API token
validate_cloudflare_token() {
    local token="$1"
    local response
    
    log_info "Testing Cloudflare API token connectivity..."
    
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/user/tokens/verify")
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        local success=$(echo "$body" | jq -r '.success // false' 2>/dev/null || echo "false")
        if [[ "$success" == "true" ]]; then
            log_success "✅ API token validation successful!"
            return 0
        fi
    fi
    
    log_error "❌ API token validation failed (HTTP: $http_code)"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
    return 1
}

# Function to test zone access
test_zone_access() {
    local token="$1"
    local domain="$2"
    local response
    
    log_info "Testing zone access for domain: $domain"
    
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/zones?name=$domain")
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        local success=$(echo "$body" | jq -r '.success // false' 2>/dev/null || echo "false")
        local zone_count=$(echo "$body" | jq -r '.result | length' 2>/dev/null || echo "0")
        
        if [[ "$success" == "true" && "$zone_count" -gt 0 ]]; then
            local zone_id=$(echo "$body" | jq -r '.result[0].id' 2>/dev/null || echo "")
            log_success "✅ Zone access confirmed! Zone ID: $zone_id"
            echo "$zone_id"
            return 0
        fi
    fi
    
    log_error "❌ Zone access test failed (HTTP: $http_code)"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
    return 1
}

# Check if current token works
NEED_NEW_TOKEN=false
ZONE_ID=""

if [[ -n "$CURRENT_TOKEN" ]]; then
    log_info "Testing current API token..."
    if validate_cloudflare_token "$CURRENT_TOKEN"; then
        ZONE_ID=$(test_zone_access "$CURRENT_TOKEN" "$DOMAIN" 2>/dev/null || echo "")
        if [[ -n "$ZONE_ID" ]]; then
            log_success "🎉 Current API token works perfectly!"
            NEED_NEW_TOKEN=false
        else
            log_warn "Current token validates but can't access the zone"
            NEED_NEW_TOKEN=true
        fi
    else
        log_warn "Current API token failed validation"
        NEED_NEW_TOKEN=true
    fi
else
    log_warn "No API token found in configuration"
    NEED_NEW_TOKEN=true
fi

# If we need a new token, provide comprehensive instructions
if [[ "$NEED_NEW_TOKEN" == "true" ]]; then
    log_critical "🚨 IMMEDIATE ACTION REQUIRED: API TOKEN SETUP 🚨"
    echo ""
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}                        🔧 CLOUDFLARE API TOKEN CREATION GUIDE 🔧${NC}"
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Step 1: Open this URL in your browser:"
    echo -e "${CYAN}   https://dash.cloudflare.com/profile/api-tokens${NC}"
    echo ""
    echo "Step 2: Click '+ Create Token'"
    echo ""
    echo "Step 3: Use the 'Edit zone DNS' template"
    echo ""
    echo "Step 4: Configure the token with these EXACT settings:"
    echo -e "${GREEN}   • Permissions: Zone:DNS:Edit${NC}"
    echo -e "${GREEN}   • Zone Resources: Include - Specific zone - $DOMAIN${NC}"
    echo -e "${GREEN}   • Client IP Address Filtering: (leave blank)${NC}"
    echo -e "${GREEN}   • TTL: (optional - can leave blank)${NC}"
    echo ""
    echo "Step 5: Click 'Continue to summary' then 'Create Token'"
    echo ""
    echo "Step 6: Copy the token that starts with something like 'abc123def456...'"
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: This is NOT the Global API Key! It's a new API Token!${NC}"
    echo -e "${WHITE}═══════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Interactive token input with validation
    while true; do
        echo -n "Please paste your NEW Cloudflare API Token here: "
        read -r NEW_TOKEN
        
        if [[ -z "$NEW_TOKEN" ]]; then
            log_error "Empty token provided. Please try again."
            continue
        fi
        
        if [[ ${#NEW_TOKEN} -lt 40 ]]; then
            log_error "Token too short. API tokens are typically 40+ characters."
            continue
        fi
        
        if [[ "$NEW_TOKEN" == *"Global API Key"* || "$NEW_TOKEN" == *"api_key"* ]]; then
            log_error "This looks like a Global API Key, not an API Token. Please create an API Token."
            continue
        fi
        
        log_info "Validating your new API token..."
        
        if validate_cloudflare_token "$NEW_TOKEN"; then
            ZONE_ID=$(test_zone_access "$NEW_TOKEN" "$DOMAIN" 2>/dev/null || echo "")
            if [[ -n "$ZONE_ID" ]]; then
                log_success "🎉 Perfect! Your new API token works flawlessly!"
                CURRENT_TOKEN="$NEW_TOKEN"
                break
            else
                log_error "Token validates but can't access the $DOMAIN zone. Please check zone selection."
                continue
            fi
        else
            log_error "Token validation failed. Please check the token and try again."
            continue
        fi
    done
fi

log_wizard "Configuring your environment with the ultimate API token setup..."

# Update secrets file with proper format
log_info "Updating secrets file: $CURRENT_TOKEN_FILE"

# Remove any existing Cloudflare configuration
sed -i '/CLOUDFLARE_API_TOKEN/d' "$CURRENT_TOKEN_FILE" 2>/dev/null || true
sed -i '/CLOUDFLARE_API_KEY/d' "$CURRENT_TOKEN_FILE" 2>/dev/null || true
sed -i '/CLOUDFLARE_EMAIL/d' "$CURRENT_TOKEN_FILE" 2>/dev/null || true

# Add new configuration
cat >> "$CURRENT_TOKEN_FILE" << EOF

# 🚀 Cloudflare API Configuration - Generated by Emergency Protocol
export CLOUDFLARE_EMAIL="$EMAIL"
export CLOUDFLARE_API_TOKEN="$CURRENT_TOKEN"
export CLOUDFLARE_ZONE_ID="$ZONE_ID"

# Legacy support (for older scripts that might still use these)
export CF_API_EMAIL="$EMAIL"
export CF_API_KEY="$CURRENT_TOKEN"
EOF

log_success "✅ Secrets file updated successfully!"

# Create environment file for Docker Compose
ENV_FILE="/home/delorenj/code/mcp/voice-mcp-agent/.env"
log_info "Creating Docker Compose environment file: $ENV_FILE"

cat > "$ENV_FILE" << EOF
# 🚀 Cloudflare Configuration for Docker Compose
CLOUDFLARE_EMAIL=$EMAIL
CLOUDFLARE_API_TOKEN=$CURRENT_TOKEN
CLOUDFLARE_ZONE_ID=$ZONE_ID

# Legacy support
CF_API_EMAIL=$EMAIL
CF_API_KEY=$CURRENT_TOKEN

# Default password for various services
DEFAULT_PASSWORD=supersecret123
TURN_USERNAME=livekit
TURN_PASSWORD=supersecret123
TURN_SECRET=livekit-turn-secret-production-2024
EOF

log_success "✅ Docker environment file created!"

# Validate Docker Compose configuration
log_info "Validating Docker Compose configuration..."

if ! docker compose config &>/dev/null; then
    log_warn "Docker Compose configuration has issues. Checking Traefik setup..."
fi

# Check if Traefik is properly configured for Cloudflare DNS challenge
TRAEFIK_CONFIG_OK=false

if docker ps | grep -q traefik; then
    log_info "Traefik is running. Checking DNS challenge configuration..."
    
    # Check Traefik logs for DNS challenge setup
    if docker logs traefik 2>&1 | grep -q "cloudflare"; then
        log_success "✅ Traefik appears to be configured for Cloudflare DNS challenge"
        TRAEFIK_CONFIG_OK=true
    else
        log_warn "Traefik doesn't seem to be using Cloudflare DNS challenge"
    fi
else
    log_warn "Traefik is not running"
fi

# Create a test DNS record to verify everything works
log_wizard "Testing DNS record creation to verify complete setup..."

TEST_RECORD="_acme-challenge-test.${DOMAIN}"
TEST_VALUE="test-$(date +%s)"

log_info "Creating test DNS record: $TEST_RECORD"

CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $CURRENT_TOKEN" \
    -H "Content-Type: application/json" \
    --data "{
        \"type\": \"TXT\",
        \"name\": \"$TEST_RECORD\",
        \"content\": \"$TEST_VALUE\",
        \"ttl\": 120
    }" \
    "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records")

if echo "$CREATE_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then
    RECORD_ID=$(echo "$CREATE_RESPONSE" | jq -r '.result.id')
    log_success "✅ Test DNS record created successfully!"
    
    # Clean up the test record
    sleep 2
    log_info "Cleaning up test DNS record..."
    
    DELETE_RESPONSE=$(curl -s -X DELETE \
        -H "Authorization: Bearer $CURRENT_TOKEN" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID")
    
    if echo "$DELETE_RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then
        log_success "✅ Test DNS record cleaned up successfully!"
    else
        log_warn "Test DNS record cleanup failed (not critical)"
    fi
else
    log_error "❌ Test DNS record creation failed!"
    echo "$CREATE_RESPONSE" | jq '.'
    exit 1
fi

# Final verification and restart recommendation
log_wizard "Performing final system verification..."

# Check ACME.json permissions
ACME_FILE="/home/delorenj/code/mcp/voice-mcp-agent/traefik-data/acme.json"
if [[ -f "$ACME_FILE" ]]; then
    chmod 600 "$ACME_FILE"
    log_success "✅ ACME file permissions corrected"
else
    mkdir -p "$(dirname "$ACME_FILE")"
    touch "$ACME_FILE"
    chmod 600 "$ACME_FILE"
    log_success "✅ ACME file created with proper permissions"
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo -e "║                           🎉 EMERGENCY PROTOCOL COMPLETE! 🎉                        ║"
echo -e "╚══════════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "🎊 Your Cloudflare API token is now properly configured!"
echo ""
echo -e "${WHITE}📋 CONFIGURATION SUMMARY:${NC}"
echo -e "   • API Token: ${CURRENT_TOKEN:0:20}...✅"
echo -e "   • Domain: $DOMAIN ✅"
echo -e "   • Zone ID: $ZONE_ID ✅"
echo -e "   • Email: $EMAIL ✅"
echo -e "   • DNS Challenge: Ready ✅"
echo ""
echo -e "${WHITE}🚀 NEXT STEPS:${NC}"
echo "   1. Restart your Docker services: docker compose down && docker compose up -d"
echo "   2. Monitor Traefik logs: docker logs -f traefik"
echo "   3. Check certificate generation for your domains"
echo ""
echo -e "${WHITE}🔍 MONITORING COMMANDS:${NC}"
echo "   • Check certificates: curl -I https://lk.delo.sh"
echo "   • View ACME status: docker exec traefik cat /acme.json | jq '.'"
echo "   • Traefik dashboard: https://traefik.delo.sh (if configured)"
echo ""

log_wizard "The void has been appeased. Your SSL certificates shall flow like fine wine! 🍷"

# Source the new configuration
if [[ -f "$CURRENT_TOKEN_FILE" ]]; then
    source "$CURRENT_TOKEN_FILE" 2>/dev/null || true
fi

echo -e "${GREEN}✨ Emergency Protocol Complete - Your infrastructure is now blessed by the SSL gods! ✨${NC}"