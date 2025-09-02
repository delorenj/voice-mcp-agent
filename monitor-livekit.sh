#!/bin/bash

# LiveKit Monitoring and Health Check Script
# Monitors LiveKit services and provides detailed status information

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="compose.yml"
LIVEKIT_DOMAIN="lk.delo.sh"
WHIP_DOMAIN="lk-whip.delo.sh"
TURN_DOMAIN="lk-turn.delo.sh"

# Health check URLs
LIVEKIT_HEALTH_URL="https://$LIVEKIT_DOMAIN/rtc/validate"
WHIP_HEALTH_URL="https://$WHIP_DOMAIN/health"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

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
    echo -e "${CYAN}ℹ $1${NC}"
}

# Check service status
check_service_status() {
    echo "======================================"
    echo "Container Status"
    echo "======================================"
    
    if docker compose -f "$COMPOSE_FILE" ps --format table; then
        echo
    else
        error "Failed to get container status"
        return 1
    fi
}

# Check health endpoints
check_health_endpoints() {
    echo "======================================"
    echo "Health Endpoint Checks"
    echo "======================================"
    
    # LiveKit server health
    if curl -f -s --max-time 10 "$LIVEKIT_HEALTH_URL" &> /dev/null; then
        success "LiveKit server health check passed"
    else
        error "LiveKit server health check failed"
    fi
    
    # WHIP endpoint health (if available)
    if curl -f -s --max-time 10 "$WHIP_HEALTH_URL" &> /dev/null; then
        success "WHIP endpoint health check passed"
    else
        warning "WHIP endpoint health check failed (may not be implemented)"
    fi
    
    echo
}

# Check network connectivity
check_network() {
    echo "======================================"
    echo "Network Connectivity"
    echo "======================================"
    
    # Check if containers are on proxy network
    local containers=("livekit-server" "livekit-ingress" "livekit-egress" "livekit-coturn")
    
    for container in "${containers[@]}"; do
        if docker inspect "$container" &> /dev/null; then
            local networks=$(docker inspect "$container" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "not_running")
            if echo "$networks" | grep -q "proxy"; then
                success "$container is connected to proxy network"
            else
                error "$container is not connected to proxy network"
            fi
        else
            warning "$container is not running"
        fi
    done
    
    echo
}

# Check Redis connectivity
check_redis() {
    echo "======================================"
    echo "Redis Connectivity"
    echo "======================================"
    
    # Check if Redis container is running
    if docker ps --format '{{.Names}}' | grep -q "redis"; then
        success "Redis container is running"
        
        # Test Redis connection from LiveKit server
        if docker exec livekit-server sh -c 'echo "ping" | timeout 5 nc redis 6379' &> /dev/null; then
            success "LiveKit server can connect to Redis"
        else
            error "LiveKit server cannot connect to Redis"
        fi
    else
        error "Redis container is not running"
    fi
    
    echo
}

# Check disk usage
check_disk_usage() {
    echo "======================================"
    echo "Disk Usage"
    echo "======================================"
    
    # Check recordings directory
    if [ -d "recordings" ]; then
        local recordings_size=$(du -sh recordings 2>/dev/null | cut -f1)
        info "Recordings directory size: $recordings_size"
    fi
    
    # Check livekit-data directory
    if [ -d "livekit-data" ]; then
        local data_size=$(du -sh livekit-data 2>/dev/null | cut -f1)
        info "LiveKit data directory size: $data_size"
    fi
    
    # Check available disk space
    local available_space=$(df -h . | awk 'NR==2 {print $4}')
    info "Available disk space: $available_space"
    
    echo
}

# Check resource usage
check_resources() {
    echo "======================================"
    echo "Resource Usage"
    echo "======================================"
    
    # Get container resource usage
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null) 2>/dev/null || {
        warning "Could not retrieve resource usage stats"
    }
    
    echo
}

# Check logs for errors
check_logs() {
    echo "======================================"
    echo "Recent Error Logs"
    echo "======================================"
    
    local containers=("livekit-server" "livekit-ingress" "livekit-egress" "livekit-coturn")
    
    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "$container"; then
            local error_count=$(docker logs --since=1h "$container" 2>&1 | grep -i error | wc -l)
            if [ "$error_count" -gt 0 ]; then
                warning "$container has $error_count errors in the last hour"
                echo "Recent errors from $container:"
                docker logs --since=1h "$container" 2>&1 | grep -i error | tail -3
                echo
            else
                success "$container has no recent errors"
            fi
        fi
    done
    
    echo
}

# Check SSL certificates
check_ssl() {
    echo "======================================"
    echo "SSL Certificate Status"
    echo "======================================"
    
    local domains=("$LIVEKIT_DOMAIN" "$WHIP_DOMAIN" "$TURN_DOMAIN")
    
    for domain in "${domains[@]}"; do
        local cert_info=$(echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "failed")
        
        if [ "$cert_info" != "failed" ]; then
            local expiry=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
            success "$domain SSL certificate valid until: $expiry"
        else
            error "$domain SSL certificate check failed"
        fi
    done
    
    echo
}

# Performance test
performance_test() {
    echo "======================================"
    echo "Performance Test"
    echo "======================================"
    
    # Test response time
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' --max-time 10 "$LIVEKIT_HEALTH_URL" 2>/dev/null || echo "failed")
    
    if [ "$response_time" != "failed" ]; then
        local response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "N/A")
        if (( $(echo "$response_time < 1.0" | bc -l 2>/dev/null || echo 0) )); then
            success "LiveKit response time: ${response_ms}ms (Good)"
        elif (( $(echo "$response_time < 3.0" | bc -l 2>/dev/null || echo 0) )); then
            warning "LiveKit response time: ${response_ms}ms (Acceptable)"
        else
            error "LiveKit response time: ${response_ms}ms (Slow)"
        fi
    else
        error "LiveKit performance test failed"
    fi
    
    echo
}

# Generate summary report
generate_summary() {
    echo "======================================"
    echo "Health Summary"
    echo "======================================"
    
    local healthy_services=0
    local total_services=0
    local containers=("livekit-server" "livekit-ingress" "livekit-egress" "livekit-coturn")
    
    for container in "${containers[@]}"; do
        ((total_services++))
        if docker ps --format '{{.Names}}' | grep -q "$container"; then
            ((healthy_services++))
        fi
    done
    
    local health_percentage=$((healthy_services * 100 / total_services))
    
    if [ $health_percentage -eq 100 ]; then
        success "All LiveKit services are running ($healthy_services/$total_services)"
    elif [ $health_percentage -ge 75 ]; then
        warning "Most LiveKit services are running ($healthy_services/$total_services)"
    else
        error "Many LiveKit services are down ($healthy_services/$total_services)"
    fi
    
    info "System health: $health_percentage%"
    
    echo
    echo "For detailed logs, run: $0 logs"
    echo "To restart services, run: ./deploy-livekit.sh restart"
}

# Show service logs
show_logs() {
    echo "======================================"
    echo "Service Logs"
    echo "======================================"
    
    docker compose -f "$COMPOSE_FILE" logs --tail=50 -f
}

# Main monitoring function
main() {
    echo "======================================"
    echo "LiveKit Monitoring Report"
    echo "Generated: $(date)"
    echo "======================================"
    echo
    
    check_service_status
    check_health_endpoints
    check_network
    check_redis
    check_disk_usage
    check_resources
    check_logs
    check_ssl
    performance_test
    generate_summary
}

# Handle script arguments
case "${1:-}" in
    "logs")
        show_logs
        ;;
    "quick")
        check_service_status
        check_health_endpoints
        generate_summary
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [logs|quick]"
        echo "  logs  - Show service logs"
        echo "  quick - Quick health check"
        echo "  (no arg) - Full monitoring report"
        exit 1
        ;;
esac