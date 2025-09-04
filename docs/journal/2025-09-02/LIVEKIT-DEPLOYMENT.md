# LiveKit Self-Hosting Deployment Guide

## 🚀 Production-Ready LiveKit Infrastructure

This deployment provides a complete, production-ready LiveKit self-hosting solution integrated with your existing Traefik proxy and Redis infrastructure.

## 📋 What's Included

### Core Services
- **LiveKit Server**: Main WebRTC server for real-time communication
- **LiveKit Ingress**: RTMP/WHIP/WebRTC input gateway for streaming
- **LiveKit Egress**: Recording and streaming output processing
- **TURN Server**: NAT traversal support for reliable connections

### Infrastructure Features
- ✅ **Traefik Integration**: Automatic SSL/TLS termination and routing
- ✅ **Redis Integration**: Uses existing Redis instance for state management
- ✅ **Health Monitoring**: Comprehensive health checks and monitoring
- ✅ **Auto-Scaling**: Container-based deployment with proper resource limits
- ✅ **Security**: Non-root containers with minimal privileges
- ✅ **Persistence**: Proper volume management for recordings and data

### Domain Configuration
- `lk.delo.sh` - Main LiveKit server (WebRTC/HTTP API)
- `lk-whip.delo.sh` - WHIP endpoint for WebRTC ingestion
- `lk-turn.delo.sh` - TURN/STUN server for NAT traversal
- `rtmp://lk.delo.sh:1935/x` - RTMP endpoint for streaming

## 🛠️ Files Overview

### Configuration Files
```
livekit-config.yaml     # Main LiveKit server configuration
ingress-config.yaml     # Ingress service configuration  
egress-config.yaml      # Egress service configuration
coturn.conf            # TURN server configuration
```

### Deployment Files
```
compose.yml            # Docker Compose configuration
.env.production        # Environment template
deploy-livekit.sh     # Deployment automation script
monitor-livekit.sh    # Monitoring and health checks
```

## 🚀 Quick Start

### 1. Prepare Environment

```bash
# Copy environment template
cp .env.production .env

# Edit environment variables (especially secrets)
nano .env
```

### 2. Deploy Services

```bash
# Run the automated deployment
./deploy-livekit.sh
```

### 3. Monitor Status

```bash
# Check service health
./monitor-livekit.sh

# View logs
./monitor-livekit.sh logs

# Quick status check
./monitor-livekit.sh quick
```

## ⚙️ Environment Configuration

### Required Variables

```bash
# LiveKit API Credentials
LIVEKIT_API_KEY=APIcQP8xHwvsq7d
LIVEKIT_API_SECRET=RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B

# Redis Configuration (uses existing instance)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${DEFAULT_PASSWORD}

# TURN Server Credentials
TURN_USERNAME=livekit
TURN_PASSWORD=${DEFAULT_PASSWORD}
TURN_SECRET=livekit-turn-secret
```

### Optional Configuration

```bash
# Resource Limits
MAX_CPU_UTILIZATION=0.8
MEMORY_LIMIT=4GB

# Media Settings
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
AUDIO_BITRATE=64000

# Logging
LOG_LEVEL=info
DEVELOPMENT=false
```

## 🔧 Management Commands

### Deployment Management
```bash
./deploy-livekit.sh          # Deploy services
./deploy-livekit.sh stop     # Stop all services
./deploy-livekit.sh restart  # Restart services
./deploy-livekit.sh status   # Check status
./deploy-livekit.sh logs     # View logs
```

### Monitoring
```bash
./monitor-livekit.sh         # Full health report
./monitor-livekit.sh quick   # Quick status check
./monitor-livekit.sh logs    # Follow logs
```

### Docker Compose Operations
```bash
# Manual service management
docker compose up -d
docker compose down
docker compose restart
docker compose logs -f

# Individual service operations
docker compose restart livekit-server
docker compose logs -f livekit-ingress
```

## 📊 Health Monitoring

The monitoring script checks:

- ✅ Container status and health
- ✅ Network connectivity (proxy network)
- ✅ Redis connectivity and authentication
- ✅ SSL certificate validity
- ✅ Endpoint response times
- ✅ Resource usage (CPU/Memory)
- ✅ Disk space and storage
- ✅ Recent error logs

### Health Endpoints

```bash
# LiveKit server health
curl https://lk.delo.sh/rtc/validate

# Container health checks
docker compose ps

# Service metrics (if enabled)
curl https://lk.delo.sh/metrics
```

## 🔐 Security Features

### Network Security
- All services run on isolated `proxy` network
- No host networking (unlike default LiveKit configs)
- Traefik handles SSL termination automatically
- Non-root containers with minimal privileges

### Authentication
- API key-based authentication for LiveKit server
- TURN server authentication for NAT traversal
- Redis password authentication
- Environment-based secret management

### Container Security
```yaml
# Example security configuration
security_opt:
  - seccomp:unconfined  # Only for media processing containers
cap_add:
  - CAP_SYS_ADMIN      # Only for egress (media processing)
```

## 📁 Storage and Persistence

### Volume Management
- `livekit-data:/data` - LiveKit server data and state
- `./recordings:/recordings` - Recording output storage
- `./templates:/templates` - Recording templates
- `./caddy_data:/data` - Caddy proxy data (if using Caddy)

### Backup Strategy
```bash
# Backup recordings
tar -czf recordings-backup-$(date +%Y%m%d).tar.gz recordings/

# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz *.yaml *.conf .env
```

## 🚨 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check container logs
docker compose logs livekit-server

# Verify network connectivity
docker network ls | grep proxy

# Check Redis connectivity
docker exec livekit-server ping redis
```

**SSL/TLS Issues:**
```bash
# Check Traefik logs
docker logs traefik

# Verify DNS resolution
nslookup lk.delo.sh

# Check certificate status
./monitor-livekit.sh | grep SSL
```

**Redis Connection Issues:**
```bash
# Check Redis container
docker ps | grep redis

# Test Redis connectivity
docker exec redis redis-cli ping

# Check network connectivity
docker exec livekit-server nc -zv redis 6379
```

### Performance Optimization

**CPU Usage High:**
- Adjust `MAX_CPU_UTILIZATION` in environment
- Consider hardware acceleration: `HARDWARE_ENCODER=auto`
- Scale services horizontally if needed

**Memory Issues:**
- Set `MEMORY_LIMIT` appropriately
- Monitor with: `docker stats`
- Check for memory leaks in logs

**Network Issues:**
- Verify TURN server configuration
- Check firewall rules for UDP ports 50000-60000
- Test with different network configurations

## 📈 Scaling and Performance

### Horizontal Scaling
```yaml
# Scale ingress services
docker compose up -d --scale livekit-ingress=2

# Load balancer configuration in Traefik
labels:
  - "traefik.http.services.livekit.loadbalancer.sticky.cookie=true"
```

### Resource Optimization
```yaml
# Container resource limits
services:
  livekit-server:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 🔗 Integration Examples

### WebRTC Client Connection
```javascript
import { Room, connect } from 'livekit-client';

const room = await connect('wss://lk.delo.sh', token, {
  adaptiveStream: true,
  dynacast: true
});
```

### RTMP Streaming
```bash
# Stream to LiveKit via RTMP
ffmpeg -i input.mp4 -c copy -f flv rtmp://lk.delo.sh:1935/x/room_name
```

### Recording with Egress
```javascript
// Start room recording
const recording = await egressClient.startRoomCompositeEgress({
  roomName: 'my-room',
  layout: 'grid',
  audioOnly: false,
  videoOnly: false,
  customBaseUrl: 'https://my-recording-template.com'
});
```

## 📚 Additional Resources

- [LiveKit Documentation](https://docs.livekit.io/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 🆘 Support

If you encounter issues:

1. **Check the monitoring output**: `./monitor-livekit.sh`
2. **Review service logs**: `./deploy-livekit.sh logs`
3. **Verify network connectivity**: Ensure Traefik and Redis are running
4. **Check configuration**: Validate YAML files and environment variables
5. **Test endpoints**: Use curl to test health endpoints

## 🎉 Success Indicators

When deployment is successful, you should see:

✅ All containers running and healthy  
✅ Health endpoints responding (200 OK)  
✅ SSL certificates valid and auto-renewing  
✅ Redis connectivity working  
✅ TURN server accessible  
✅ No errors in recent logs  

Welcome to your new production-ready LiveKit infrastructure! 🚀