#!/bin/bash
# Simple SSL Fix - Just get it working

echo "🔧 SIMPLE SSL FIX"
echo "================="

# Clean slate approach
echo "🧹 Cleaning up certificates..."
cd /home/delorenj/docker/trunk-main/core/traefik
docker compose down
sudo rm -f traefik-data/acme.json
touch traefik-data/acme.json
chmod 600 traefik-data/acme.json

# Use CF_DNS_API_TOKEN format that Traefik expects
echo "📝 Setting up Cloudflare credentials..."
cat > .env << EOF
CLOUDFLARE_EMAIL=delorenj@delo.sh
CF_DNS_API_TOKEN=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg
CLOUDFLARE_DNS_API_TOKEN=8uS4nHflVYMGq6m6YysHWQLKRVZMk83A-Z0gQOtg
EOF

# Start Traefik
echo "🚀 Starting Traefik..."
docker compose up -d

# Wait for startup
sleep 15

# Start LiveKit services
echo "🚀 Starting LiveKit services..."
cd /home/delorenj/code/mcp/voice-mcp-agent
docker compose up -d

# Wait for certificate requests
echo "⏳ Waiting for certificate generation..."
sleep 45

# Test results
echo "🔍 Testing SSL certificates..."
./QUICK-SSL-CHECK.sh

echo "✅ Simple SSL fix complete!"
