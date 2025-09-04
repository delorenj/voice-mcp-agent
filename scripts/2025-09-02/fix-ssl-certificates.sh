#!/bin/bash

# LiveKit SSL Certificate Fix Script
# Fixes Cloudflare credentials and SSL certificate generation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

echo "======================================"
echo "LiveKit SSL Certificate Fix"
echo "======================================"
echo

# Check if Cloudflare credentials are set
check_cloudflare_credentials() {
    log "Checking Cloudflare credentials..."
    
    if [ -z "${CLOUDFLARE_EMAIL:-}" ] || [ -z "${CLOUDFLARE_API_KEY:-}" ]; then
        error "Cloudflare credentials are not set in environment"
        echo
        echo "Please set the following environment variables:"
        echo "  export CLOUDFLARE_EMAIL='jaradd@gmail.com'"
        echo "  export CLOUDFLARE_API_KEY='your-global-api-key'"
        echo
        echo "Get your Global API Key from: https://dash.cloudflare.com/profile/api-tokens"
        echo
        echo "Add these to /home/delorenj/.config/zshyzsh/secrets.zsh and reload your shell:"
        echo "  source /home/delorenj/.config/zshyzsh/secrets.zsh"
        echo
        return 1
    else
        success "Cloudflare credentials found in environment"
        return 0
    fi
}

# Update Traefik environment file
update_traefik_env() {
    log "Updating Traefik environment file..."
    
    local traefik_env="/home/delorenj/docker/trunk-main/core/traefik/.env"
    
    cat > "$traefik_env" << EOF
# Traefik Environment Variables
# SSL Certificate Generation via Cloudflare DNS Challenge

# Cloudflare API Credentials for Let's Encrypt DNS Challenge
CLOUDFLARE_EMAIL=${CLOUDFLARE_EMAIL}
CLOUDFLARE_API_KEY=${CLOUDFLARE_API_KEY}
EOF
    
    chmod 600 "$traefik_env"
    success "Traefik environment file updated"
}

# Restart Traefik with new credentials
restart_traefik() {
    log "Restarting Traefik with new credentials..."
    
    cd /home/delorenj/docker/trunk-main/core/traefik
    
    # Stop Traefik
    docker compose down traefik
    
    # Wait a moment
    sleep 5
    
    # Start Traefik with new credentials
    docker compose up -d traefik
    
    success "Traefik restarted"
}

# Restart LiveKit services
restart_livekit() {
    log "Restarting LiveKit services..."
    
    cd /home/delorenj/code/mcp/voice-mcp-agent
    
    # Stop all services
    docker compose down
    
    # Wait for cleanup
    sleep 5
    
    # Start services
    docker compose up -d
    
    success "LiveKit services restarted"
}

# Wait for SSL certificates to generate
wait_for_certificates() {
    log "Waiting for SSL certificates to generate..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Checking certificate generation... (attempt $attempt/$max_attempts)"
        
        if curl -k -s https://lk.delo.sh/rtc/validate > /dev/null 2>&1; then
            success "SSL certificates generated successfully!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            warning "Certificate generation taking longer than expected"
            log "Check Traefik logs: docker logs traefik"
            break
        fi
        
        sleep 10
        ((attempt++))
    done
}

# Test SSL endpoints
test_ssl_endpoints() {
    log "Testing SSL endpoints..."
    
    local endpoints=(
        "https://lk.delo.sh/rtc/validate"
        "https://lk-whip.delo.sh"
        "https://lk-turn.delo.sh"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -k -s -I "$endpoint" | grep -q "200\|404\|401"; then
            success "✅ $endpoint - SSL working"
        else
            warning "⚠️  $endpoint - SSL issues detected"
        fi
    done
}

# Main execution
main() {
    if check_cloudflare_credentials; then
        update_traefik_env
        restart_traefik
        sleep 10
        restart_livekit
        wait_for_certificates
        test_ssl_endpoints
        
        echo
        success "SSL certificate fix completed!"
        echo
        echo "Next steps:"
        echo "1. Check service status: docker compose ps"
        echo "2. Monitor Traefik logs: docker logs traefik"
        echo "3. Test LiveKit endpoints: curl -I https://lk.delo.sh/rtc/validate"
        echo
    else
        error "Cannot proceed without Cloudflare credentials"
        exit 1
    fi
}

main "$@"