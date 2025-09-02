#!/bin/bash
# 🔍 CLOUDFLARE API TOKEN COMPREHENSIVE TESTING SUITE 🔍
# Version: "The Paranoid Edition"
#
# This script tests EVERY aspect of your Cloudflare API token
# with the thoroughness of a CIA background check
#
# Author: Your Obsessive-Compulsive DevOps Engineer 🤖

set -euo pipefail

# Colors (because monochrome output is for peasants)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
DOMAIN="${DOMAIN:-delo.sh}"
EMAIL="${EMAIL:-delorenj@delo.sh}"
SECRETS_FILE="/home/delorenj/.config/zshyzsh/secrets.zsh"
ENV_FILE="./.env"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions with extra flair
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

log_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${CYAN}[TEST $TOTAL_TESTS]${NC} $1"
}

log_pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "         ${GREEN}✅ PASS${NC} - $1"
}

log_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "         ${RED}❌ FAIL${NC} - $1"
}

log_skip() {
    echo -e "         ${YELLOW}⏭️  SKIP${NC} - $1"
}

# Banner that would make marketing teams weep with envy
echo -e "${PURPLE}"
echo "╔════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                      🔍 CLOUDFLARE API TOKEN TESTING SUITE 🔍                                  ║"
echo "║                                The Paranoid Edition™                                           ║"
echo "║                                                                                                ║"
echo "║                    Testing every conceivable aspect of your API token                          ║"
echo "║                           with obsessive-compulsive precision                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

sleep 2

log_info "🚀 Initializing comprehensive API token testing protocol..."

# Function to load token from various sources
load_api_token() {
    local token=""
    
    log_test "Loading API token from configuration files"
    
    # Try to load from secrets file
    if [[ -f "$SECRETS_FILE" ]]; then
        if grep -q "CLOUDFLARE_API_TOKEN" "$SECRETS_FILE"; then
            token=$(grep "CLOUDFLARE_API_TOKEN" "$SECRETS_FILE" | head -1 | sed 's/.*"\(.*\)".*/\1/')
            if [[ -n "$token" ]]; then
                log_pass "Token loaded from secrets file"
                echo "$token"
                return 0
            fi
        fi
        
        if grep -q "CLOUDFLARE_API_KEY" "$SECRETS_FILE"; then
            token=$(grep "CLOUDFLARE_API_KEY" "$SECRETS_FILE" | head -1 | sed 's/.*"\(.*\)".*/\1/')
            if [[ -n "$token" ]]; then
                log_pass "Legacy API key found in secrets file"
                echo "$token"
                return 0
            fi
        fi
    fi
    
    # Try to load from .env file
    if [[ -f "$ENV_FILE" ]]; then
        if grep -q "CLOUDFLARE_API_TOKEN" "$ENV_FILE"; then
            token=$(grep "CLOUDFLARE_API_TOKEN" "$ENV_FILE" | head -1 | cut -d'=' -f2)
            if [[ -n "$token" ]]; then
                log_pass "Token loaded from .env file"
                echo "$token"
                return 0
            fi
        fi
    fi
    
    # Try environment variable
    if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
        log_pass "Token loaded from environment variable"
        echo "$CLOUDFLARE_API_TOKEN"
        return 0
    fi
    
    log_fail "No API token found in any configuration source"
    return 1
}

# Function to test basic API connectivity
test_api_connectivity() {
    local token="$1"
    local response http_code body
    
    log_test "Testing basic Cloudflare API connectivity"
    
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --connect-timeout 10 \
        --max-time 30 \
        "https://api.cloudflare.com/client/v4/user/tokens/verify" 2>/dev/null || echo "000")
    
    if [[ ${#response} -lt 3 ]]; then
        log_fail "No response from Cloudflare API"
        return 1
    fi
    
    http_code="${response: -3}"
    body="${response%???}"
    
    case "$http_code" in
        200)
            local success=$(echo "$body" | jq -r '.success // false' 2>/dev/null || echo "false")
            if [[ "$success" == "true" ]]; then
                log_pass "API connectivity successful (HTTP 200)"
                return 0
            else
                log_fail "API returned success=false"
                echo "$body" | jq '.' 2>/dev/null || echo "$body"
                return 1
            fi
            ;;
        401)
            log_fail "Authentication failed - Invalid API token (HTTP 401)"
            return 1
            ;;
        403)
            log_fail "Authorization failed - Insufficient permissions (HTTP 403)"
            return 1
            ;;
        429)
            log_fail "Rate limit exceeded (HTTP 429)"
            return 1
            ;;
        000)
            log_fail "Connection failed - Network or DNS issue"
            return 1
            ;;
        *)
            log_fail "Unexpected HTTP response code: $http_code"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
            return 1
            ;;
    esac
}

# Function to test token permissions
test_token_permissions() {
    local token="$1"
    local response http_code body
    
    log_test "Analyzing token permissions and scope"
    
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --connect-timeout 10 \
        --max-time 30 \
        "https://api.cloudflare.com/client/v4/user/tokens/verify" 2>/dev/null || echo "000")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        local permissions=$(echo "$body" | jq -r '.result.policies[0].permission_groups[] // empty' 2>/dev/null || echo "")
        
        if echo "$permissions" | grep -q "dns"; then
            log_pass "DNS permissions confirmed"
        else
            log_fail "DNS permissions not found"
            return 1
        fi
        
        local resources=$(echo "$body" | jq -r '.result.policies[0].resources // empty' 2>/dev/null || echo "")
        if [[ -n "$resources" ]]; then
            log_pass "Resource restrictions found (zone-specific token)"
        else
            log_pass "Global token permissions detected"
        fi
        
        return 0
    else
        log_fail "Could not verify token permissions"
        return 1
    fi
}

# Function to test zone access
test_zone_access() {
    local token="$1"
    local domain="$2"
    local response http_code body zone_id
    
    log_test "Testing zone access for domain: $domain"
    
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --connect-timeout 10 \
        --max-time 30 \
        "https://api.cloudflare.com/client/v4/zones?name=$domain" 2>/dev/null || echo "000")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        local success=$(echo "$body" | jq -r '.success // false' 2>/dev/null || echo "false")
        local zone_count=$(echo "$body" | jq -r '.result | length' 2>/dev/null || echo "0")
        
        if [[ "$success" == "true" && "$zone_count" -gt 0 ]]; then
            zone_id=$(echo "$body" | jq -r '.result[0].id' 2>/dev/null || echo "")
            local zone_name=$(echo "$body" | jq -r '.result[0].name' 2>/dev/null || echo "")
            local zone_status=$(echo "$body" | jq -r '.result[0].status' 2>/dev/null || echo "")
            
            log_pass "Zone access confirmed"
            log_info "  Zone ID: $zone_id"
            log_info "  Zone Name: $zone_name"
            log_info "  Zone Status: $zone_status"
            
            echo "$zone_id"
            return 0
        else
            log_fail "Zone not found or inaccessible"
            return 1
        fi
    else
        log_fail "Zone access test failed (HTTP: $http_code)"
        return 1
    fi
}

# Function to test DNS record operations
test_dns_operations() {
    local token="$1"
    local zone_id="$2"
    local domain="$3"
    
    log_test "Testing DNS record operations (CREATE/DELETE)"
    
    # Create test record
    local test_name="_acme-challenge-test-$(date +%s)"
    local test_content="v=test-$(date +%s)"
    local record_id
    
    log_info "Creating test TXT record: $test_name.$domain"
    
    local create_response
    create_response=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --data "{
            \"type\": \"TXT\",
            \"name\": \"$test_name\",
            \"content\": \"$test_content\",
            \"ttl\": 120
        }" \
        "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records" 2>/dev/null)
    
    if echo "$create_response" | jq -e '.success == true' >/dev/null 2>&1; then
        record_id=$(echo "$create_response" | jq -r '.result.id')
        log_pass "DNS record created successfully (ID: $record_id)"
        
        # Test record retrieval
        log_info "Verifying record exists..."
        local get_response
        get_response=$(curl -s -H "Authorization: Bearer $token" \
            "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records/$record_id" 2>/dev/null)
        
        if echo "$get_response" | jq -e '.success == true' >/dev/null 2>&1; then
            log_pass "DNS record retrieval successful"
        else
            log_fail "DNS record retrieval failed"
        fi
        
        # Clean up - delete the test record
        sleep 2
        log_info "Cleaning up test record..."
        
        local delete_response
        delete_response=$(curl -s -X DELETE \
            -H "Authorization: Bearer $token" \
            "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records/$record_id" 2>/dev/null)
        
        if echo "$delete_response" | jq -e '.success == true' >/dev/null 2>&1; then
            log_pass "DNS record deleted successfully"
            return 0
        else
            log_fail "DNS record deletion failed (cleanup issue)"
            return 1
        fi
    else
        log_fail "DNS record creation failed"
        echo "$create_response" | jq '.' 2>/dev/null || echo "$create_response"
        return 1
    fi
}

# Function to test ACME challenge simulation
test_acme_challenge() {
    local token="$1"
    local zone_id="$2"
    local domain="$3"
    
    log_test "Simulating ACME DNS challenge workflow"
    
    # Simulate what Traefik/Let's Encrypt would do
    local challenge_name="_acme-challenge.test-$(date +%s)"
    local challenge_token="$(openssl rand -base64 32 | tr -d '=\n')"
    
    log_info "Creating ACME challenge record: $challenge_name.$domain"
    
    local create_response
    create_response=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        --data "{
            \"type\": \"TXT\",
            \"name\": \"$challenge_name\",
            \"content\": \"$challenge_token\",
            \"ttl\": 60
        }" \
        "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records" 2>/dev/null)
    
    if echo "$create_response" | jq -e '.success == true' >/dev/null 2>&1; then
        local record_id=$(echo "$create_response" | jq -r '.result.id')
        log_pass "ACME challenge record created"
        
        # Wait for DNS propagation (simulate ACME delay)
        log_info "Waiting for DNS propagation (15 seconds)..."
        sleep 15
        
        # Try to resolve the DNS record
        log_info "Testing DNS resolution..."
        local dns_result
        dns_result=$(dig +short TXT "$challenge_name.$domain" @8.8.8.8 2>/dev/null || echo "")
        
        if [[ -n "$dns_result" ]]; then
            log_pass "DNS propagation successful"
        else
            log_warn "DNS propagation slow (not critical for this test)"
        fi
        
        # Clean up
        log_info "Cleaning up ACME challenge record..."
        curl -s -X DELETE \
            -H "Authorization: Bearer $token" \
            "https://api.cloudflare.com/client/v4/zones/$zone_id/dns_records/$record_id" >/dev/null 2>&1
        
        log_pass "ACME challenge simulation completed"
        return 0
    else
        log_fail "ACME challenge record creation failed"
        return 1
    fi
}

# Function to test Docker environment integration
test_docker_integration() {
    log_test "Testing Docker Compose environment integration"
    
    # Check if .env file has proper format
    if [[ -f "$ENV_FILE" ]]; then
        if grep -q "CLOUDFLARE_API_TOKEN" "$ENV_FILE"; then
            log_pass ".env file contains CLOUDFLARE_API_TOKEN"
        else
            log_fail ".env file missing CLOUDFLARE_API_TOKEN"
        fi
        
        if grep -q "CLOUDFLARE_EMAIL" "$ENV_FILE"; then
            log_pass ".env file contains CLOUDFLARE_EMAIL"
        else
            log_fail ".env file missing CLOUDFLARE_EMAIL"
        fi
    else
        log_fail ".env file not found"
        return 1
    fi
    
    # Test Docker Compose config
    if command -v docker >/dev/null 2>&1; then
        if docker compose config >/dev/null 2>&1; then
            log_pass "Docker Compose configuration valid"
        else
            log_fail "Docker Compose configuration invalid"
        fi
    else
        log_skip "Docker not available for testing"
    fi
    
    return 0
}

# Function to generate summary report
generate_report() {
    echo ""
    echo -e "${WHITE}╔════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                                    📊 TEST RESULTS SUMMARY 📊                                  ║"
    echo -e "╚════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    local pass_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    echo -e "${WHITE}📈 STATISTICS:${NC}"
    echo -e "   Total Tests: $TOTAL_TESTS"
    echo -e "   Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "   Failed: ${RED}$FAILED_TESTS${NC}"
    echo -e "   Success Rate: ${GREEN}${pass_rate}%${NC}"
    echo ""
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED! Your Cloudflare API token is perfectly configured!${NC}"
        echo ""
        echo -e "${WHITE}✅ READY FOR:${NC}"
        echo -e "   • Traefik ACME DNS challenges"
        echo -e "   • Let's Encrypt certificate generation"
        echo -e "   • Automated SSL certificate renewal"
        echo -e "   • Production deployment"
        echo ""
        echo -e "${CYAN}🚀 You can now safely start your services with: docker compose up -d${NC}"
        
    elif [[ $PASSED_TESTS -gt $FAILED_TESTS ]]; then
        echo -e "${YELLOW}⚠️  MOSTLY WORKING with some issues. Review failed tests above.${NC}"
        echo ""
        echo -e "${WHITE}🔧 LIKELY FIXES:${NC}"
        echo -e "   • Run: ./cloudflare-api-emergency-fix.sh"
        echo -e "   • Check API token permissions in Cloudflare dashboard"
        echo -e "   • Verify domain is correctly configured"
        
    else
        echo -e "${RED}❌ CRITICAL ISSUES DETECTED! API token configuration needs attention.${NC}"
        echo ""
        echo -e "${WHITE}🚨 IMMEDIATE ACTIONS:${NC}"
        echo -e "   1. Run: ./cloudflare-api-emergency-fix.sh"
        echo -e "   2. Create new API token with proper permissions"
        echo -e "   3. Verify domain ownership in Cloudflare"
        echo -e "   4. Re-run this test script"
    fi
    
    echo ""
    echo -e "${WHITE}📞 SUPPORT:${NC}"
    echo -e "   • Re-run this test: ./test-cloudflare-api.sh"
    echo -e "   • Emergency fix: ./cloudflare-api-emergency-fix.sh"
    echo -e "   • Monitor Traefik: docker logs -f traefik"
    echo ""
}

# Main execution flow
main() {
    log_info "Starting comprehensive Cloudflare API token testing..."
    
    # Load API token
    local api_token
    if ! api_token=$(load_api_token); then
        log_error "Cannot proceed without API token. Run ./cloudflare-api-emergency-fix.sh first!"
        exit 1
    fi
    
    log_info "API Token: ${api_token:0:20}..."
    echo ""
    
    # Test 1: Basic connectivity
    if ! test_api_connectivity "$api_token"; then
        log_error "Basic API connectivity failed. Aborting remaining tests."
        generate_report
        exit 1
    fi
    echo ""
    
    # Test 2: Token permissions
    test_token_permissions "$api_token"
    echo ""
    
    # Test 3: Zone access
    local zone_id
    if zone_id=$(test_zone_access "$api_token" "$DOMAIN"); then
        echo ""
        
        # Test 4: DNS operations
        test_dns_operations "$api_token" "$zone_id" "$DOMAIN"
        echo ""
        
        # Test 5: ACME challenge simulation
        test_acme_challenge "$api_token" "$zone_id" "$DOMAIN"
        echo ""
    else
        log_error "Zone access failed. Skipping DNS operation tests."
        echo ""
    fi
    
    # Test 6: Docker integration
    test_docker_integration
    echo ""
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Check dependencies
if ! command -v curl >/dev/null 2>&1; then
    log_error "curl is required but not installed"
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    log_error "jq is required but not installed"
    exit 1
fi

# Run main function
main "$@"