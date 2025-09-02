#!/bin/bash
# 🚨 ULTIMATE SSL CERTIFICATE EMERGENCY DEPLOYMENT 🚨
# Version: "The One-Click Wonder Edition"
#
# This script deploys a BULLETPROOF SSL setup that's so automated,
# it makes DevOps engineers obsolete (just kidding, we still need you!)
#
# Author: Your Friendly Neighborhood Infrastructure Wizard 🧙‍♂️

set -euo pipefail

# Colors (because life is too short for boring terminal output)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="delo.sh"
EMAIL="delorenj@delo.sh"

# Logging functions with extra pizzazz
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

log_step() {
    echo -e "${CYAN}${BOLD}[STEP $1]${NC} $2"
}

# Epic banner that strikes fear into SSL demons
show_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        🚨 SSL EMERGENCY DEPLOYMENT PROTOCOL 🚨                                  ║"
    echo "║                                The One-Click Wonder™                                             ║"
    echo "║                                                                                                  ║"
    echo "║                     Fully automated SSL certificate deployment                                   ║"
    echo "║                    that works so well, it's almost embarrassing                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_step "1" "Checking system prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    for tool in docker curl jq dig openssl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt update && sudo apt install -y ${missing_tools[*]}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose v2 required. Install Docker Compose v2."
        exit 1
    fi
    
    # Check if running as correct user
    if [[ $(whoami) != "delorenj" ]]; then
        log_warn "Not running as expected user 'delorenj'. Some paths may not work."
    fi
    
    log_success "✅ All prerequisites satisfied!"
}

# Setup Cloudflare API token
setup_cloudflare_api() {
    log_step "2" "Setting up Cloudflare API token..."
    
    if [[ -x "./cloudflare-api-emergency-fix.sh" ]]; then
        log_info "Running Cloudflare API emergency fix..."
        ./cloudflare-api-emergency-fix.sh
    else
        log_error "Cloudflare emergency fix script not found or not executable"
        exit 1
    fi
    
    log_success "✅ Cloudflare API token configured!"
}

# Test API connectivity
test_api_setup() {
    log_step "3" "Testing Cloudflare API setup..."
    
    if [[ -x "./test-cloudflare-api.sh" ]]; then
        log_info "Running comprehensive API tests..."
        if ./test-cloudflare-api.sh; then
            log_success "✅ All API tests passed!"
        else
            log_error "❌ API tests failed. Check the output above."
            exit 1
        fi
    else
        log_error "Cloudflare test script not found or not executable"
        exit 1
    fi
}

# Setup Docker network
setup_docker_network() {
    log_step "4" "Setting up Docker networks..."
    
    # Create proxy network if it doesn't exist
    if ! docker network inspect proxy >/dev/null 2>&1; then
        log_info "Creating proxy network..."
        docker network create proxy
        log_success "✅ Proxy network created!"
    else
        log_info "Proxy network already exists"
    fi
}

# Prepare Traefik data directory
prepare_traefik_data() {
    log_step "5" "Preparing Traefik data directory..."
    
    # Create directory structure
    mkdir -p traefik-data/{logs,config}
    
    # Create acme.json with proper permissions
    touch traefik-data/acme.json
    chmod 600 traefik-data/acme.json
    
    # Create dynamic configuration directory
    mkdir -p traefik-data/config
    
    log_success "✅ Traefik data directory prepared!"
}

# Deploy Traefik with optimized configuration
deploy_traefik() {
    log_step "6" "Deploying Traefik with Cloudflare DNS challenge..."
    
    # Check if we have the optimized configuration
    if [[ ! -f "traefik-cloudflare-optimizer.yml" ]]; then
        log_error "Optimized Traefik configuration not found!"
        exit 1
    fi
    
    # Stop existing Traefik if running
    if docker ps | grep -q traefik; then
        log_info "Stopping existing Traefik container..."
        docker compose down traefik 2>/dev/null || docker stop traefik 2>/dev/null || true
    fi
    
    # Deploy with optimized configuration
    log_info "Starting Traefik with optimized configuration..."
    docker compose -f traefik-cloudflare-optimizer.yml up -d traefik
    
    # Wait for Traefik to be ready
    log_info "Waiting for Traefik to initialize..."
    sleep 10
    
    # Check if Traefik is running
    if docker ps | grep -q traefik; then
        log_success "✅ Traefik deployed successfully!"
    else
        log_error "❌ Traefik deployment failed!"
        docker logs traefik 2>/dev/null | tail -20 || true
        exit 1
    fi
}

# Test SSL certificate generation
test_ssl_generation() {
    log_step "7" "Testing SSL certificate generation..."
    
    # Deploy test service
    log_info "Deploying test service (whoami)..."
    docker compose -f traefik-cloudflare-optimizer.yml up -d whoami
    
    # Wait for certificate generation
    log_info "Waiting for SSL certificate generation (this may take 2-3 minutes)..."
    
    local retries=0
    local max_retries=36  # 3 minutes with 5-second intervals
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -s -I "https://whoami.$DOMAIN" | grep -q "200 OK"; then
            log_success "✅ SSL certificate generated and working!"
            break
        fi
        
        retries=$((retries + 1))
        echo -n "."
        sleep 5
    done
    
    if [[ $retries -ge $max_retries ]]; then
        log_error "❌ SSL certificate generation timed out"
        log_info "Check Traefik logs: docker logs traefik"
        return 1
    fi
    
    echo ""  # New line after dots
}

# Deploy your application services
deploy_applications() {
    log_step "8" "Deploying application services..."
    
    # Check if main compose file exists
    if [[ -f "compose.yml" ]]; then
        log_info "Deploying application services from compose.yml..."
        docker compose up -d
        
        log_success "✅ Application services deployed!"
    else
        log_info "No compose.yml found, skipping application deployment"
    fi
}

# Monitor and verify deployment
monitor_deployment() {
    log_step "9" "Monitoring deployment status..."
    
    echo ""
    echo -e "${WHITE}📊 DEPLOYMENT STATUS:${NC}"
    echo ""
    
    # Check running containers
    log_info "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(traefik|livekit|whoami)"
    echo ""
    
    # Check certificates
    log_info "Checking SSL certificates..."
    
    # Test whoami service
    if curl -s -I "https://whoami.$DOMAIN" | grep -q "200 OK"; then
        echo -e "   ${GREEN}✅ whoami.$DOMAIN${NC} - SSL working"
    else
        echo -e "   ${RED}❌ whoami.$DOMAIN${NC} - SSL not working"
    fi
    
    # Test main LiveKit service
    if curl -s -I "https://lk.$DOMAIN" | grep -q "200\\|404\\|403"; then
        echo -e "   ${GREEN}✅ lk.$DOMAIN${NC} - SSL working (service may not be ready)"
    else
        echo -e "   ${YELLOW}⏳ lk.$DOMAIN${NC} - Certificate pending"
    fi
    
    echo ""
    
    # Show ACME status
    log_info "ACME certificate status:"
    if docker exec traefik cat /acme.json 2>/dev/null | jq -e '.letsencrypt.Certificates | length' >/dev/null 2>&1; then
        local cert_count=$(docker exec traefik cat /acme.json | jq '.letsencrypt.Certificates | length' 2>/dev/null)
        echo -e "   ${GREEN}✅ $cert_count certificate(s) stored${NC}"
    else
        echo -e "   ${YELLOW}⏳ No certificates stored yet${NC}"
    fi
    
    echo ""
}

# Provide post-deployment instructions
show_post_deployment_info() {
    log_step "10" "Post-deployment information and monitoring..."
    
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗"
    echo -e "║                             🎉 DEPLOYMENT COMPLETE! 🎉                              ║"
    echo -e "╚══════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${WHITE}🌐 AVAILABLE SERVICES:${NC}"
    echo -e "   • Test Service: ${CYAN}https://whoami.$DOMAIN${NC}"
    echo -e "   • LiveKit Server: ${CYAN}https://lk.$DOMAIN${NC}"
    echo -e "   • Traefik Dashboard: ${CYAN}https://traefik.$DOMAIN${NC} (if configured)"
    echo ""
    
    echo -e "${WHITE}📊 MONITORING COMMANDS:${NC}"
    echo -e "   • Traefik logs: ${YELLOW}docker logs -f traefik${NC}"
    echo -e "   • Container status: ${YELLOW}docker ps${NC}"
    echo -e "   • Certificate status: ${YELLOW}docker exec traefik cat /acme.json | jq '.letsencrypt.Certificates'${NC}"
    echo -e "   • Test certificates: ${YELLOW}curl -I https://whoami.$DOMAIN${NC}"
    echo ""
    
    echo -e "${WHITE}🔧 CONFIGURATION FILES:${NC}"
    echo -e "   • Traefik config: ${YELLOW}traefik-cloudflare-optimizer.yml${NC}"
    echo -e "   • Environment vars: ${YELLOW}.env${NC}"
    echo -e "   • ACME storage: ${YELLOW}traefik-data/acme.json${NC}"
    echo ""
    
    echo -e "${WHITE}🚨 TROUBLESHOOTING:${NC}"
    echo -e "   • Re-run tests: ${YELLOW}./test-cloudflare-api.sh${NC}"
    echo -e "   • Fix API token: ${YELLOW}./cloudflare-api-emergency-fix.sh${NC}"
    echo -e "   • Restart Traefik: ${YELLOW}docker compose restart traefik${NC}"
    echo -e "   • Clear certificates: ${YELLOW}rm traefik-data/acme.json && docker compose restart traefik${NC}"
    echo ""
    
    log_wizard "🎊 Your SSL setup is now BULLETPROOF! The void is pleased with your offering!"
}

# Error handling
trap 'log_error "❌ Emergency deployment failed at step $current_step. Check the logs above for details."' ERR

# Main execution flow
main() {
    local current_step=0
    
    show_banner
    sleep 2
    
    current_step=1; check_prerequisites
    current_step=2; setup_cloudflare_api
    current_step=3; test_api_setup
    current_step=4; setup_docker_network
    current_step=5; prepare_traefik_data
    current_step=6; deploy_traefik
    current_step=7; test_ssl_generation
    current_step=8; deploy_applications
    current_step=9; monitor_deployment
    current_step=10; show_post_deployment_info
    
    log_wizard "✨ EMERGENCY DEPLOYMENT COMPLETE! Your infrastructure is now blessed by the SSL gods! ✨"
}

# Change to script directory
cd "$SCRIPT_DIR"

# Run main function
main "$@"