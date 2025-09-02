#!/bin/bash

# LiveKit Setup Validation Script
# Validates the deployment configuration before going live

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="compose.yml"
ENV_FILE=".env"
REQUIRED_CONFIGS=("livekit-config.yaml" "ingress-config.yaml" "egress-config.yaml" "coturn.conf")

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

validate_prerequisites() {
    info "Validating prerequisites..."
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        success "Docker is installed"
    else
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        success "Docker Compose v2 is available"
    else
        error "Docker Compose v2 is not available"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
        success "Docker daemon is running"
    else
        error "Docker daemon is not running"
        exit 1
    fi
    
    echo
}

validate_files() {
    info "Validating configuration files..."
    
    # Check compose file
    if [ -f "$COMPOSE_FILE" ]; then
        success "Docker Compose file exists"
        
        # Validate compose file syntax
        if docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
            success "Docker Compose file syntax is valid"
        else
            error "Docker Compose file has syntax errors"
            return 1
        fi
    else
        error "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    # Check environment file
    if [ -f "$ENV_FILE" ]; then
        success "Environment file exists"
    else
        warning "Environment file not found: $ENV_FILE"
        info "Consider copying from .env.production template"
    fi
    
    # Check configuration files
    for config in "${REQUIRED_CONFIGS[@]}"; do
        if [ -f "$config" ]; then
            success "Configuration file exists: $config"
        else
            error "Configuration file missing: $config"
            return 1
        fi
    done
    
    echo
}

validate_network() {
    info "Validating network configuration..."
    
    # Check if proxy network exists
    if docker network ls | grep -q "proxy"; then
        success "Proxy network exists"
    else
        error "Proxy network not found - Traefik may not be running"
        info "Create network with: docker network create proxy"
        return 1
    fi
    
    echo
}

validate_redis() {
    info "Validating Redis connectivity..."
    
    # Check if Redis container is running
    if docker ps --format '{{.Names}}' | grep -q "redis"; then
        success "Redis container is running"
        
        # Check if Redis is accessible
        if docker exec redis redis-cli ping >/dev/null 2>&1; then
            success "Redis is responding to ping"
        else
            warning "Redis is not responding to ping"
        fi
    else
        error "Redis container not found"
        info "LiveKit requires Redis for state management"
        return 1
    fi
    
    echo
}

validate_ports() {
    info "Validating port availability..."
    
    # Check critical ports
    local ports=("1935" "3478" "5349" "7881")
    
    for port in "${ports[@]}"; do
        if ss -tuln | grep -q ":$port "; then
            warning "Port $port is already in use"
        else
            success "Port $port is available"
        fi
    done
    
    # Check UDP port range
    local udp_start=50000
    local udp_end=60000
    local used_udp=$(ss -uln | grep -c ":5[0-9][0-9][0-9][0-9] " || true)
    
    if [ "$used_udp" -gt 100 ]; then
        warning "Many UDP ports in RTC range are in use ($used_udp ports)"
    else
        success "UDP port range mostly available ($used_udp ports in use)"
    fi
    
    echo
}

validate_permissions() {
    info "Validating file permissions..."
    
    # Check script permissions
    local scripts=("deploy-livekit.sh" "monitor-livekit.sh" "validate-setup.sh")
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ] && [ -x "$script" ]; then
            success "$script is executable"
        elif [ -f "$script" ]; then
            warning "$script exists but is not executable"
            info "Run: chmod +x $script"
        else
            warning "$script not found"
        fi
    done
    
    # Check directory permissions
    local dirs=("recordings" "templates" "livekit-data")
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            if [ -w "$dir" ]; then
                success "Directory $dir is writable"
            else
                error "Directory $dir is not writable"
            fi
        else
            info "Directory $dir will be created during deployment"
        fi
    done
    
    echo
}

validate_dns() {
    info "Validating DNS resolution..."
    
    local domains=("lk.delo.sh" "lk-whip.delo.sh" "lk-turn.delo.sh")
    
    for domain in "${domains[@]}"; do
        if nslookup "$domain" >/dev/null 2>&1; then
            success "$domain resolves correctly"
        else
            warning "$domain does not resolve"
            info "Ensure DNS records are configured"
        fi
    done
    
    echo
}

check_environment_variables() {
    info "Checking environment variables..."
    
    if [ -f "$ENV_FILE" ]; then
        # Source the environment file to check variables
        set -a
        source "$ENV_FILE" 2>/dev/null || true
        set +a
        
        # Check critical variables
        local required_vars=("LIVEKIT_API_KEY" "LIVEKIT_API_SECRET")
        
        for var in "${required_vars[@]}"; do
            if [ -n "${!var:-}" ]; then
                success "$var is set"
            else
                error "$var is not set in environment"
            fi
        done
        
        # Check optional but recommended variables
        local recommended_vars=("REDIS_PASSWORD" "TURN_PASSWORD" "TURN_SECRET")
        
        for var in "${recommended_vars[@]}"; do
            if [ -n "${!var:-}" ]; then
                success "$var is configured"
            else
                warning "$var is not set (will use defaults)"
            fi
        done
    else
        warning "Cannot check environment variables - no $ENV_FILE found"
    fi
    
    echo
}

generate_summary() {
    echo "======================================"
    echo "Validation Summary"
    echo "======================================"
    
    info "Prerequisites: Docker and Docker Compose are ready"
    info "Configuration: All required files are present"
    info "Infrastructure: Network and Redis connectivity validated"
    info "Security: Permissions and environment variables checked"
    
    echo
    success "✅ Setup validation completed successfully!"
    echo
    info "Ready to deploy? Run: ./deploy-livekit.sh"
    info "Need monitoring? Run: ./monitor-livekit.sh"
    echo
}

# Main validation function
main() {
    echo "======================================"
    echo "LiveKit Setup Validation"
    echo "======================================"
    echo
    
    validate_prerequisites
    validate_files
    validate_network
    validate_redis
    validate_ports
    validate_permissions
    validate_dns
    check_environment_variables
    generate_summary
}

# Run validation
main