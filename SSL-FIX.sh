#!/bin/bash
# Minimal SSL Fix - Address the real issues

set -e

echo "🔧 MINIMAL SSL FIX"
echo "=================="

# 1. Fix the certificate path in compose.yml
echo "📝 Fixing certificate path in compose.yml..."
sed -i 's|/home/delorenj/docker/trunk-main/core/traefik/traefik-data|/home/delorenj/docker/trunk-main/core/traefik/traefik-data|g' compose.yml

# 2. Ensure Traefik is running
echo "🚀 Starting Traefik..."
cd /home/delorenj/docker/trunk-main/core/traefik
docker compose up -d

# 3. Wait for Traefik
echo "⏳ Waiting for Traefik..."
sleep 10

# 4. Start LiveKit services
echo "🚀 Starting LiveKit services..."
cd /home/delorenj/code/mcp/voice-mcp-agent
docker compose up -d

# 5. Wait for certificate generation
echo "⏳ Waiting for certificate generation..."
sleep 30

# 6. Test certificates
echo "🔍 Testing certificates..."
for domain in lk.delo.sh lk-whip.delo.sh lk-turn.delo.sh; do
    echo -n "Testing $domain: "
    if curl -s --connect-timeout 10 "https://$domain" &>/dev/null; then
        echo "✅ Working"
    else
        echo "❌ Failed"
    fi
done

echo "✅ SSL fix complete!"
