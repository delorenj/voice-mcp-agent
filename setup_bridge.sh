#!/bin/bash
# setup_bridge.sh - Setup and deploy Mac Bridge integration

set -e

echo "🔧 Setting up Mac Bridge Integration"
echo "==================================="

# Check if running from correct directory
if [[ ! -f "compose.yml" ]]; then
    echo "❌ Error: Please run this script from the voice-mcp-agent directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "📋 Checking dependencies..."

if ! command_exists docker; then
    echo "❌ Docker is required but not installed"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is required but not installed"
    exit 1
fi

echo "✅ Dependencies check passed"

# Build bridge Docker image
echo "🏗️  Building bridge Docker image..."
docker build -f Dockerfile.bridge -t livekit-mac-bridge:latest .

# Update requirements in existing containers (if needed)
echo "📦 Updating Python dependencies..."
if docker ps -q -f name=livekit-server | grep -q .; then
    echo "   Updating existing LiveKit container..."
    # Note: In production, you'd rebuild the main container too
    # For now, we'll just install in the bridge container
fi

# Create backup of existing compose file
if [[ -f "compose.yml.backup" ]]; then
    echo "   Backup already exists: compose.yml.backup"
else
    echo "   Creating backup: compose.yml.backup"
    cp compose.yml compose.yml.backup
fi

# Start/restart services
echo "🚀 Starting services..."
docker-compose up -d mac-bridge

# Wait for bridge service to be healthy
echo "⏱️  Waiting for bridge service to be ready..."
timeout=60
elapsed=0
while [[ $elapsed -lt $timeout ]]; do
    if docker ps -f name=livekit-mac-bridge --format "table {{.Status}}" | grep -q "healthy\|Up"; then
        echo "✅ Bridge service is running"
        break
    fi
    
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
done

if [[ $elapsed -ge $timeout ]]; then
    echo ""
    echo "⚠️  Timeout waiting for bridge service. Check logs with:"
    echo "   docker-compose logs mac-bridge"
    exit 1
fi

# Test bridge connectivity
echo "🧪 Testing bridge integration..."
python3 bridge_integration_test.py --server ws://localhost:8765/bridge

# Display connection information
echo ""
echo "🎉 Mac Bridge Setup Complete!"
echo "============================="
echo ""
echo "🔗 Connection Information:"
echo "   Local WebSocket:  ws://localhost:8765/bridge"
echo "   Public WebSocket: wss://lk.delo.sh/bridge"
echo ""
echo "📱 Mac Client Setup:"
echo "   1. Install dependencies on Mac:"
echo "      pip install websockets pyautogui"
echo ""
echo "   2. Download mac_client.py to your Mac:"
echo "      scp $(hostname):$(pwd)/mac_client.py ~/mac_client.py"
echo ""
echo "   3. Run Mac client:"
echo "      python3 ~/mac_client.py --server wss://lk.delo.sh/bridge --mode both"
echo ""
echo "🔄 Available Modes:"
echo "   --mode type     # Only type transcribed text"
echo "   --mode command  # Only execute agent commands"  
echo "   --mode both     # Both typing and commands (recommended)"
echo ""
echo "🛠️  Management Commands:"
echo "   View logs:      docker-compose logs -f mac-bridge"
echo "   Restart:        docker-compose restart mac-bridge"
echo "   Stop bridge:    docker-compose stop mac-bridge"
echo "   Remove bridge:  docker-compose rm mac-bridge"
echo ""
echo "🧪 Test Commands:"
echo "   Integration test: python3 bridge_integration_test.py"
echo "   Local test:      python3 mac_client.py --server ws://localhost:8765/bridge --mode both"
echo ""
echo "📝 Next Steps:"
echo "   1. Test local connection with LiveKit web interface"
echo "   2. Setup Mac client and test remote connection"
echo "   3. Configure any firewall rules if needed"
echo "   4. Monitor bridge logs for any issues"
echo ""

# Show current status
echo "📊 Current Status:"
docker-compose ps mac-bridge