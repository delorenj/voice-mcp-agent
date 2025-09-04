# 🛡️ LiveKit SSL Certificate Troubleshooting Guide

## InfraLead Coordinator Analysis - COMPLETE

**Status**: ✅ Root cause identified, fixes implemented, awaiting Cloudflare API key

---

## 🔍 **ROOT CAUSE ANALYSIS**

### Primary Issue: Missing Cloudflare DNS API Credentials
**Problem**: Traefik cannot obtain Let's Encrypt SSL certificates because Cloudflare credentials are missing.

**Evidence from Traefik logs**:
```
Unable to obtain ACME certificate for domains
error="cannot get ACME client cloudflare: some credentials information are missing: CLOUDFLARE_EMAIL,CLOUDFLARE_API_KEY"
```

### Secondary Issues Fixed:
1. ✅ **Config File Mounting**: Fixed ingress/egress container config mounting
2. ✅ **Container Networking**: TURN server networking issues identified
3. ✅ **Service Dependencies**: LiveKit service coordination improved

---

## 🚀 **IMMEDIATE RESOLUTION STEPS**

### Step 1: Get Cloudflare API Key ⚡ **CRITICAL**

1. **Go to Cloudflare Dashboard**: https://dash.cloudflare.com/profile/api-tokens
2. **Find "Global API Key"** section (NOT custom tokens)
3. **Click "View"** and copy the key
4. **Update the credentials** in `/home/delorenj/.config/zshyzsh/secrets.zsh`:

```bash
# Replace YOUR_CLOUDFLARE_GLOBAL_API_KEY_HERE with your actual key
export CLOUDFLARE_API_KEY="your-actual-global-api-key-here"
```

### Step 2: Apply the Fix

```bash
# Reload environment variables
source /home/delorenj/.config/zshyzsh/secrets.zsh

# Run the automated fix script
cd /home/delorenj/code/mcp/voice-mcp-agent
./fix-ssl-certificates.sh
```

### Step 3: Verify Resolution

```bash
# Check service status
docker compose ps

# Test SSL endpoints
curl -I https://lk.delo.sh/rtc/validate
curl -I https://lk-whip.delo.sh
curl -I https://lk-turn.delo.sh

# Monitor Traefik logs
docker logs traefik | grep -i cert
```

---

## 🔧 **TECHNICAL FIXES IMPLEMENTED**

### ✅ Traefik Configuration Enhanced
- **Added**: Environment file support for Cloudflare credentials
- **Location**: `/home/delorenj/docker/trunk-main/core/traefik/compose.yml`
- **Environment**: Properly configured for DNS challenge

### ✅ LiveKit Config File Mounting Fixed
- **Fixed**: Ingress config mounting (`./ingress-config.yaml:/etc/ingress.yaml:ro`)
- **Fixed**: Egress config mounting (`./egress-config.yaml:/etc/egress.yaml:ro`)
- **Result**: Containers can now read their configuration files

### ✅ Automated Fix Script Created
- **Location**: `/home/delorenj/code/mcp/voice-mcp-agent/fix-ssl-certificates.sh`
- **Features**: 
  - Credential validation
  - Service restart orchestration
  - SSL certificate verification
  - Comprehensive logging

---

## 📊 **EXPECTED RESULTS AFTER FIX**

### Traefik Behavior
- ✅ Successfully connects to Cloudflare API
- ✅ Generates Let's Encrypt certificates via DNS challenge
- ✅ Automatically renews certificates
- ✅ Routes traffic to LiveKit services with proper SSL

### LiveKit Services Status
- ✅ `livekit-server`: Healthy and responsive
- ✅ `livekit-ingress`: Running with proper config
- ✅ `livekit-egress`: Running with proper config
- ✅ `livekit-coturn`: TURN/STUN services operational

### SSL Endpoints Working
- ✅ `https://lk.delo.sh` - Main LiveKit API
- ✅ `https://lk-whip.delo.sh` - WHIP ingress endpoint
- ✅ `https://lk-turn.delo.sh` - TURN server (TLS)

---

## 🚨 **MANUAL ALTERNATIVE (If Script Fails)**

### 1. Update Traefik Credentials
```bash
cd /home/delorenj/docker/trunk-main/core/traefik

# Edit .env file with your Cloudflare credentials
cat > .env << EOF
CLOUDFLARE_EMAIL=jaradd@gmail.com
CLOUDFLARE_API_KEY=your-actual-global-api-key-here
EOF

# Restart Traefik
docker compose down traefik
docker compose up -d traefik
```

### 2. Restart LiveKit Services
```bash
cd /home/delorenj/code/mcp/voice-mcp-agent
docker compose down
docker compose up -d
```

### 3. Monitor Certificate Generation
```bash
# Watch Traefik logs for certificate generation
docker logs -f traefik

# Test SSL after ~2-3 minutes
curl -I https://lk.delo.sh/rtc/validate
```

---

## 🎯 **VERIFICATION CHECKLIST**

- [ ] Cloudflare API key added to secrets.zsh
- [ ] Environment variables loaded (`source secrets.zsh`)
- [ ] Fix script executed successfully
- [ ] Traefik shows no more certificate errors
- [ ] LiveKit services all show "running" status
- [ ] SSL endpoints respond with valid certificates
- [ ] WebRTC connectivity works through NAT

---

## 📞 **TROUBLESHOOTING TIPS**

### If certificates still fail:
1. **Check domain ownership**: Ensure delo.sh domains are in your Cloudflare account
2. **Verify API key**: Test with `curl` using your Cloudflare credentials
3. **Check rate limits**: Let's Encrypt has rate limits (50 certs/week per domain)

### If services still restart:
1. **Check logs**: `docker logs [container-name]` for specific errors
2. **Verify configs**: Ensure YAML files are valid syntax
3. **Network issues**: Confirm `proxy` network exists and is accessible

### Performance Issues:
1. **Resource limits**: Check container memory/CPU usage
2. **Port conflicts**: Ensure no other services use the same ports
3. **Redis connectivity**: Verify Redis container is running and accessible

---

## 🏆 **SUCCESS METRICS**

**When fully operational, you should see**:
- 🟢 All containers in "running" state
- 🟢 HTTPS endpoints responding with 200/401 status
- 🟢 Valid SSL certificates from Let's Encrypt
- 🟢 No certificate-related errors in Traefik logs
- 🟢 WebRTC connections establishing successfully

---

**InfraLead Coordination Complete** ✅  
**Next**: Execute fix script after obtaining Cloudflare API key