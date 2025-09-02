#!/bin/bash

# LiveKit Deployment Script - Production Ready
# Deploys LiveKit infrastructure with Traefik integration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="compose.yml"
ENV_FILE=".env"
LIVEKIT_CONFIG="livekit-config.yaml"
INGRESS_CONFIG="ingress-config.yaml"
EGRESS_CONFIG="egress-config.yaml"

# Logging function
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

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker compose &> /dev/null; then
        error "Docker Compose is not available. Please install Docker Compose v2."
        exit 1
    fi
    
    # Check if proxy network exists
    if ! docker network ls | grep -q "proxy"; then
        error "Proxy network does not exist. Please ensure Traefik is running."
        exit 1
    fi
    
    # Check if Redis is running
    if ! docker ps | grep -q "redis"; then
        warning "Redis container not found. LiveKit requires Redis to function."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    success "Prerequisites check completed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p recordings
    mkdir -p templates
    mkdir -p livekit-data
    mkdir -p caddy_data
    
    # Set proper permissions
    chmod 755 recordings templates livekit-data caddy_data
    
    success "Directories created"
}

# Generate environment file if it doesn't exist
generate_env() {
    if [ ! -f "$ENV_FILE" ]; then
        log "Generating environment file..."
        
        if [ -f ".env.production" ]; then
            cp .env.production "$ENV_FILE"
            warning "Environment file created from template. Please review and update values."
        else
            error "No environment template found. Please create $ENV_FILE manually."
            exit 1
        fi
    else
        log "Environment file already exists"
    fi
}

# Validate configuration files
validate_configs() {
    log "Validating configuration files..."
    
    local configs=("$LIVEKIT_CONFIG" "$INGRESS_CONFIG" "$EGRESS_CONFIG")
    
    for config in "${configs[@]}"; do
        if [ ! -f "$config" ]; then
            error "Configuration file $config not found"
            exit 1
        fi
    done
    
    # Validate compose file
    if ! docker compose -f "$COMPOSE_FILE" config &> /dev/null; then
        error "Docker Compose configuration is invalid"
        exit 1
    fi
    
    success "Configuration validation completed"
}

# Pull Docker images
pull_images() {
    log "Pulling Docker images..."
    
    docker compose -f "$COMPOSE_FILE" pull
    
    success "Images pulled successfully"
}

# Deploy LiveKit services
deploy_services() {
    log "Deploying LiveKit services..."
    
    # Stop existing services if running
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
    
    # Start services
    docker compose -f "$COMPOSE_FILE" up -d
    
    success "Services deployed"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy\|running"; then
            log "Services are starting up... (attempt $attempt/$max_attempts)"
            break
        fi
        
        sleep 2
        ((attempt++))
    done
    
    # Give services additional time to fully initialize
    sleep 10
    
    success "Services are ready"
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    
    # Test LiveKit server health
    if curl -f -s https://lk.delo.sh/rtc/validate &> /dev/null; then
        success "LiveKit server is responding"
    else
        warning "LiveKit server health check failed (this may be normal during initial startup)"
    fi
    
    # Check container status
    docker compose -f "$COMPOSE_FILE" ps
}

# Show deployment status
show_status() {
    echo
    echo "======================================"
    echo "LiveKit Deployment Complete!"
    echo "======================================"
    echo
    echo "URLs:"
    echo "  LiveKit Server:    https://lk.delo.sh"
    echo "  WHIP Endpoint:     https://lk-whip.delo.sh"
    echo "  TURN Server:       lk-turn.delo.sh:5349"
    echo
    echo "RTMP Endpoint:       rtmp://lk.delo.sh:1935/x"
    echo
    echo "Management:"
    echo "  View logs:         docker compose -f $COMPOSE_FILE logs -f"
    echo "  Restart services:  docker compose -f $COMPOSE_FILE restart"
    echo "  Stop services:     docker compose -f $COMPOSE_FILE down"
    echo
    echo "Configuration files:"
    echo "  Main config:       $LIVEKIT_CONFIG"
    echo "  Ingress config:    $INGRESS_CONFIG"
    echo "  Egress config:     $EGRESS_CONFIG"
    echo "  Environment:       $ENV_FILE"
    echo
}

# Main deployment function
main() {
    echo "======================================"
    echo "LiveKit Deployment Script"
    echo "======================================"
    echo
    
    check_prerequisites
    create_directories
    generate_env
    validate_configs
    pull_images
    deploy_services
    wait_for_services
    test_deployment
    show_status
    
    success "LiveKit deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "stop")
        log "Stopping LiveKit services..."
        docker compose -f "$COMPOSE_FILE" down
        success "Services stopped"
        ;;
    "restart")
        log "Restarting LiveKit services..."
        docker compose -f "$COMPOSE_FILE" restart
        success "Services restarted"
        ;;
    "logs")
        log "Showing service logs..."
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    "status")
        log "Service status:"
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [stop|restart|logs|status]"
        echo "  stop     - Stop all LiveKit services"
        echo "  restart  - Restart all LiveKit services"  
        echo "  logs     - Show service logs"
        echo "  status   - Show service status"
        echo "  (no arg) - Deploy LiveKit services"
        exit 1
        ;;
esac