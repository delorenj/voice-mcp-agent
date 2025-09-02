# LiveKit Deployment Troubleshooting Guide

## Quick Diagnosis Commands

```bash
# Service Status Overview
docker-compose ps
docker-compose logs --tail=50
systemctl status docker

# Network Connectivity
netstat -tulpn | grep -E "(443|7880|6379|1935|8080|5349|3478)"
curl -I http://localhost:7880/health
redis-cli -h localhost -p 6379 ping

# SSL Certificate Check
openssl s_client -connect lk.delo.sh:443 -servername lk.delo.sh
curl -I https://lk.delo.sh

# Resource Usage
docker stats
df -h
free -h
ps aux | grep -E "(caddy|livekit|redis)"
```

---

## Service-Specific Issues

### LiveKit Server Issues

#### **Issue**: LiveKit service won't start

**Symptoms:**
- Container exits immediately
- "Connection refused" on port 7880
- Health check endpoint unavailable

**Diagnosis:**
```bash
# Check container logs
docker-compose logs livekit

# Validate configuration
docker-compose exec livekit cat /etc/livekit.yaml

# Test configuration
docker run --rm -v $(pwd)/lk.delo.sh/livekit.yaml:/etc/livekit.yaml \
  livekit/livekit-server:latest --config /etc/livekit.yaml --validate
```

**Common Causes & Solutions:**

1. **Invalid configuration format**
   ```yaml
   # Fix YAML syntax errors
   port: 7880  # Ensure proper indentation
   bind_addresses:
     - ""      # Quotes required for empty string
   ```

2. **Redis connection failure**
   ```yaml
   # Update Redis configuration
   redis:
     address: redis-host:6379  # Replace <redis-host>
     username: ""
     password: ""
   ```

3. **Port binding conflicts**
   ```bash
   # Find conflicting processes
   sudo lsof -i :7880
   # Kill conflicting process or change port
   ```

4. **Insufficient permissions**
   ```bash
   # Fix directory permissions
   sudo chown -R 1000:1000 ./lk.delo.sh/
   sudo chmod -R 755 ./lk.delo.sh/
   ```

#### **Issue**: WebRTC connections failing

**Symptoms:**
- Audio/video streams not connecting
- ICE connection failures
- TURN server errors

**Diagnosis:**
```bash
# Check TURN server
telnet lk-turn.delo.sh 5349
telnet lk-turn.delo.sh 3478

# Check port range accessibility  
nmap -p 50000-50010 your-server-ip

# Validate external IP configuration
curl -4 ifconfig.me
```

**Solutions:**

1. **Configure external IP**
   ```yaml
   rtc:
     use_external_ip: true
     # Add explicit external IP if auto-detection fails
     external_ip: "your.public.ip"
   ```

2. **Firewall configuration**
   ```bash
   # Allow RTC port range
   sudo ufw allow 50000:60000/udp
   sudo ufw allow 50000:60000/tcp
   ```

3. **TURN server configuration**
   ```yaml
   turn:
     enabled: true
     domain: lk-turn.delo.sh
     tls_port: 5349
     udp_port: 3478
     external_tls: true
   ```

#### **Issue**: High CPU/Memory usage

**Symptoms:**
- Server becomes unresponsive
- High resource utilization
- OOM (Out of Memory) kills

**Diagnosis:**
```bash
# Monitor resource usage
docker stats livekit
htop -p $(pgrep livekit)

# Check for memory leaks
cat /proc/$(pgrep livekit)/status | grep -E "(VmRSS|VmSize)"
```

**Solutions:**

1. **Adjust resource limits**
   ```yaml
   # docker-compose.yaml
   services:
     livekit:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 4G
   ```

2. **Optimize configuration**
   ```yaml
   # Reduce port range if not needed
   rtc:
     port_range_start: 50000
     port_range_end: 50100  # Smaller range
   ```

---

### Caddy Proxy Issues

#### **Issue**: SSL certificate generation failing

**Symptoms:**
- "certificate signed by unknown authority"
- HTTPS connections failing
- Let's Encrypt rate limit errors

**Diagnosis:**
```bash
# Check Caddy logs
docker-compose logs caddy | grep -i cert

# Test ACME challenge
curl -I http://lk.delo.sh/.well-known/acme-challenge/test

# Check DNS resolution
nslookup lk.delo.sh
dig +short lk.delo.sh
```

**Solutions:**

1. **DNS configuration issues**
   ```bash
   # Ensure DNS points to correct IP
   dig +short lk.delo.sh
   # Should return your server's public IP
   ```

2. **Firewall blocking ACME challenge**
   ```bash
   # Allow HTTP for ACME challenge
   sudo ufw allow 80/tcp
   ```

3. **Rate limiting from Let's Encrypt**
   ```bash
   # Wait for rate limit reset (usually 1 hour)
   # Or use staging environment for testing
   ```

4. **Domain validation failure**
   ```yaml
   # Ensure all domains are accessible
   apps:
     tls:
       certificates:
         automate:
           - lk.delo.sh        # Must be reachable
           - lk-turn.delo.sh   # Must be reachable  
           - lk-whip.delo.sh   # Must be reachable
   ```

#### **Issue**: SNI routing not working

**Symptoms:**
- Wrong certificate served
- Connection to wrong backend
- "Server name doesn't match certificate"

**Diagnosis:**
```bash
# Test SNI for each domain
openssl s_client -connect lk.delo.sh:443 -servername lk.delo.sh
openssl s_client -connect lk.delo.sh:443 -servername lk-turn.delo.sh
openssl s_client -connect lk.delo.sh:443 -servername lk-whip.delo.sh
```

**Solutions:**

1. **Fix SNI configuration**
   ```yaml
   layer4:
     servers:
       main:
         routes:
           - match:
             - tls:
                 sni:
                   - "lk-turn.delo.sh"  # Exact match required
   ```

2. **Certificate SAN configuration**
   ```bash
   # Verify certificate includes all domains
   openssl x509 -in cert.pem -text -noout | grep -A1 "Subject Alternative Name"
   ```

#### **Issue**: High latency through proxy

**Symptoms:**
- Slow response times
- Connection timeouts
- Poor streaming quality

**Diagnosis:**
```bash
# Test direct vs proxy latency
time curl -I http://localhost:7880/health
time curl -I https://lk.delo.sh/

# Check proxy configuration
docker-compose exec caddy caddy validate --config /etc/caddy.yaml
```

**Solutions:**

1. **Enable connection reuse**
   ```yaml
   # Add connection pooling
   handle:
     - handler: proxy
       upstreams:
         - dial: ["localhost:7880"]
       health_checks:
         active:
           interval: 30s
   ```

2. **Optimize buffer sizes**
   ```yaml
   # Increase proxy buffers
   handle:
     - handler: proxy
       buffer_requests: true
       buffer_responses: true
   ```

---

### Redis Issues

#### **Issue**: Redis connection failures

**Symptoms:**
- "Connection refused" errors
- Session data not persisting
- LiveKit can't connect to Redis

**Diagnosis:**
```bash
# Test Redis connectivity
redis-cli -h localhost -p 6379 ping
telnet localhost 6379

# Check Redis logs
docker-compose logs redis
redis-cli info server
```

**Solutions:**

1. **Redis not running**
   ```bash
   # Start Redis service
   docker-compose up -d redis
   # Or system service
   sudo systemctl start redis-server
   ```

2. **Network binding issues**
   ```bash
   # Check Redis binding
   redis-cli config get bind
   # Should show "0.0.0.0" or specific IPs
   ```

3. **Authentication issues**
   ```yaml
   # Update LiveKit Redis config
   redis:
     address: localhost:6379
     username: ""              # Add if Redis has auth
     password: "your_password" # Add if Redis has auth
   ```

#### **Issue**: Redis memory issues

**Symptoms:**
- OOM errors
- Slow performance
- High memory usage

**Diagnosis:**
```bash
# Check Redis memory usage
redis-cli info memory
redis-cli config get maxmemory*

# Monitor Redis operations
redis-cli monitor | head -20
```

**Solutions:**

1. **Configure memory limits**
   ```bash
   # Set Redis memory limit
   redis-cli config set maxmemory 1gb
   redis-cli config set maxmemory-policy allkeys-lru
   ```

2. **Enable persistence optimization**
   ```bash
   # Configure RDB snapshots
   redis-cli config set save "900 1 300 10 60 10000"
   ```

---

### Ingress/Egress Issues

#### **Issue**: RTMP streams not working

**Symptoms:**
- RTMP connection refused
- Streams not appearing in LiveKit
- Authentication failures

**Diagnosis:**
```bash
# Test RTMP endpoint
telnet lk.delo.sh 1935

# Check ingress logs
docker-compose logs ingress

# Test with ffmpeg
ffmpeg -re -i test.mp4 -c copy -f flv rtmp://lk.delo.sh:1935/x/test-room
```

**Solutions:**

1. **Port accessibility**
   ```bash
   # Check firewall
   sudo ufw status | grep 1935
   sudo ufw allow 1935/tcp
   ```

2. **Authentication configuration**
   ```yaml
   # Verify ingress config
   api_key: APIcQP8xHwvsq7d
   api_secret: RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B
   ws_url: wss://lk.delo.sh
   ```

3. **Stream URL format**
   ```bash
   # Correct RTMP URL format
   rtmp://lk.delo.sh:1935/x/ROOM_NAME?token=JWT_TOKEN
   ```

#### **Issue**: WHIP endpoint not responding

**Symptoms:**
- HTTP 404 on WHIP endpoint
- WebRTC negotiation failures
- SDP exchange errors

**Diagnosis:**
```bash
# Test WHIP endpoint
curl -X POST https://lk-whip.delo.sh/w/test-room \
  -H "Content-Type: application/sdp" \
  -d "test-sdp"

# Check ingress service
docker-compose logs ingress | grep whip
```

**Solutions:**

1. **Service binding**
   ```yaml
   # Ensure WHIP port is configured
   whip_port: 8080
   http_relay_port: 9090
   ```

2. **Caddy routing**
   ```yaml
   # Verify WHIP domain routing
   - match:
     - tls:
         sni:
           - "lk-whip.delo.sh"
     handle:
       - handler: proxy
         upstreams:
           - dial: ["localhost:8080"]
   ```

---

## Network & Connectivity Issues

### **Issue**: DNS resolution problems

**Symptoms:**
- Services can't resolve domain names
- Certificate generation failing
- Client connection issues

**Diagnosis:**
```bash
# Test DNS resolution
nslookup lk.delo.sh
dig +short lk.delo.sh 8.8.8.8
host lk.delo.sh

# Check DNS from containers
docker-compose exec livekit nslookup lk.delo.sh
```

**Solutions:**

1. **DNS propagation**
   ```bash
   # Check DNS propagation globally
   dig @8.8.8.8 lk.delo.sh
   dig @1.1.1.1 lk.delo.sh
   ```

2. **Local DNS cache**
   ```bash
   # Clear local DNS cache
   sudo systemctl flush-dns
   sudo dscacheutil -flushcache  # macOS
   ```

3. **Container DNS**
   ```yaml
   # Set custom DNS in docker-compose
   services:
     livekit:
       dns:
         - 8.8.8.8
         - 1.1.1.1
   ```

### **Issue**: Firewall blocking connections

**Symptoms:**
- Connections timeout
- Services unreachable from external networks
- Partial functionality

**Diagnosis:**
```bash
# Check firewall status
sudo ufw status verbose
sudo iptables -L -n

# Test port accessibility
nmap -p 443,7880,6379 your-server-ip
telnet your-server-ip 443
```

**Solutions:**

1. **Configure UFW firewall**
   ```bash
   # Allow required ports
   sudo ufw allow 22/tcp      # SSH
   sudo ufw allow 80/tcp      # HTTP (for ACME)
   sudo ufw allow 443/tcp     # HTTPS
   sudo ufw allow 7880/tcp    # LiveKit HTTP
   sudo ufw allow 7881/tcp    # LiveKit RTC TCP  
   sudo ufw allow 3478/udp    # TURN UDP
   sudo ufw allow 5349/tcp    # TURN TLS
   sudo ufw allow 1935/tcp    # RTMP
   sudo ufw allow 8080/tcp    # WHIP
   sudo ufw allow 50000:60000/udp  # RTC port range
   sudo ufw --force enable
   ```

2. **Docker and firewall**
   ```bash
   # Docker might bypass UFW, check iptables
   sudo iptables -L DOCKER-USER
   
   # Add Docker-specific rules if needed
   sudo iptables -I DOCKER-USER -p tcp --dport 7880 -j ACCEPT
   ```

---

## Performance Issues

### **Issue**: High latency/poor performance

**Symptoms:**
- Slow response times
- Audio/video lag
- Connection drops

**Diagnosis:**
```bash
# System performance
htop
iostat -x 1 10
sar -u 1 10

# Network performance
iftop
netstat -i
ss -tuln

# Application performance
docker stats
curl -w "@curl-format.txt" -o /dev/null -s https://lk.delo.sh/
```

**Solutions:**

1. **System optimization**
   ```bash
   # Increase file descriptors
   echo "* soft nofile 65536" >> /etc/security/limits.conf
   echo "* hard nofile 65536" >> /etc/security/limits.conf
   
   # Optimize network settings
   echo 'net.core.somaxconn = 4096' >> /etc/sysctl.conf
   echo 'net.ipv4.tcp_max_syn_backlog = 4096' >> /etc/sysctl.conf
   sysctl -p
   ```

2. **Docker optimization**
   ```yaml
   # Optimize Docker configuration
   services:
     livekit:
       ulimits:
         nofile:
           soft: 65536
           hard: 65536
   ```

3. **Application tuning**
   ```yaml
   # LiveKit performance tuning
   rtc:
     congestion_control: true
     adaptive_stream: true
   ```

### **Issue**: Memory leaks/high memory usage

**Symptoms:**
- Memory usage constantly increasing
- OOM kills
- System becoming unresponsive

**Diagnosis:**
```bash
# Monitor memory over time
watch -n 5 'free -h && docker stats --no-stream'

# Check for memory leaks
valgrind --tool=memcheck --track-origins=yes your-app

# Analyze process memory
cat /proc/PID/smaps | grep -i pss | awk '{s+=$2} END {print s}'
```

**Solutions:**

1. **Resource limits**
   ```yaml
   # Set container memory limits
   services:
     livekit:
       deploy:
         resources:
           limits:
             memory: 2G
       restart: unless-stopped
   ```

2. **Memory monitoring**
   ```bash
   # Add memory monitoring alerts
   # Using Prometheus/Alertmanager
   ```

---

## Security Issues

### **Issue**: Authentication failures

**Symptoms:**
- "Unauthorized" errors
- API key validation failures
- JWT token errors

**Diagnosis:**
```bash
# Test API authentication
curl -H "Authorization: Bearer YOUR_TOKEN" https://lk.delo.sh/

# Validate JWT tokens
echo "YOUR_JWT" | base64 -d

# Check API key configuration
grep -r "api_key" lk.delo.sh/
```

**Solutions:**

1. **API key configuration**
   ```yaml
   # Ensure consistent API keys across services
   # In livekit.yaml:
   keys:
     APIcQP8xHwvsq7d: RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B
   
   # In ingress.yaml and egress.yaml:
   api_key: APIcQP8xHwvsq7d
   api_secret: RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B
   ```

2. **Token generation**
   ```python
   # Generate proper JWT tokens
   import jwt
   
   token = jwt.encode({
       'iss': 'APIcQP8xHwvsq7d',
       'sub': 'user-id',
       'exp': int(time.time()) + 3600  # 1 hour
   }, 'RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B', algorithm='HS256')
   ```

### **Issue**: SSL/TLS security warnings

**Symptoms:**
- Browser security warnings
- Weak cipher suite alerts
- Certificate trust issues

**Diagnosis:**
```bash
# Security assessment
sslscan lk.delo.sh:443
testssl.sh lk.delo.sh:443

# Check SSL Labs rating
curl -s "https://api.ssllabs.com/api/v3/analyze?host=lk.delo.sh"
```

**Solutions:**

1. **Caddy TLS configuration**
   ```yaml
   # Enforce strong TLS
   apps:
     tls:
       defaults:
         cipher_suites: [
           "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
           "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
           "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
           "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
         ]
         curves: ["x25519", "secp256r1", "secp384r1"]
   ```

---

## Common Error Messages

### LiveKit Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `bind: address already in use` | Port conflict | Change port or kill conflicting process |
| `connection refused` | Service not running | Start service and check configuration |
| `redis: connection refused` | Redis unreachable | Verify Redis configuration and connectivity |
| `failed to generate turn credentials` | TURN misconfiguration | Check TURN domain and ports |
| `ice connection failed` | Network/firewall issues | Open required ports and check connectivity |

### Caddy Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `certificate signed by unknown authority` | SSL cert issues | Check DNS and ACME configuration |
| `upstream server not available` | Backend unreachable | Verify upstream service is running |
| `too many redirects` | Redirect loop | Fix redirect configuration |
| `TLS handshake timeout` | TLS configuration issue | Check cipher suites and TLS settings |

### Redis Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NOAUTH Authentication required` | Missing auth | Configure password or disable auth |
| `Out of memory` | Memory limit exceeded | Increase memory limit or optimize usage |
| `Can't save in background` | Disk space/permissions | Check disk space and permissions |

---

## Emergency Procedures

### Complete Service Restart
```bash
# Stop all services
docker-compose down

# Clear any stale data (if safe)
docker system prune -f

# Restart services
docker-compose up -d

# Verify health
docker-compose ps
curl -I http://localhost:7880/health
```

### Rollback Deployment
```bash
# Rollback to previous version
git checkout HEAD~1
docker-compose down
docker-compose up -d --build

# Or use tagged version
docker-compose down
sed -i 's/:latest/:v1.0.0/' docker-compose.yaml
docker-compose up -d
```

### Emergency Certificate Fix
```bash
# If SSL certificates are broken
# Generate self-signed certificate temporarily
openssl req -x509 -nodes -days 30 -newkey rsa:2048 \
  -keyout temp.key -out temp.crt \
  -subj "/CN=lk.delo.sh"

# Update Caddy config to use manual certificates temporarily
# Then restart and fix ACME configuration
```

---

## Getting Help

### Log Collection
```bash
# Collect all relevant logs
mkdir -p troubleshooting-$(date +%Y%m%d-%H%M)
cd troubleshooting-$(date +%Y%m%d-%H%M)

# Service logs
docker-compose logs > docker-logs.txt
journalctl -u docker > system-docker.log

# System info
uname -a > system-info.txt
df -h > disk-usage.txt
free -h > memory-usage.txt
docker version > docker-version.txt
docker-compose version > compose-version.txt

# Configuration
cp -r ../lk.delo.sh/ config-backup/
cp ../docker-compose.yaml .

# Network info
ss -tuln > network-connections.txt
iptables -L -n > firewall-rules.txt
```

### Support Channels
1. **GitHub Issues**: Create detailed issue with logs and configuration
2. **LiveKit Community**: Join Discord/Slack for community help
3. **Professional Support**: Contact LiveKit team for enterprise support

### Creating Support Requests
Include:
1. Complete error messages and logs
2. System configuration (OS, Docker versions)
3. Network topology and firewall rules
4. Steps to reproduce the issue
5. Any recent changes made to the system