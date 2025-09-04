# Mac Bridge Implementation Plan

## Overview
Create a bridge that connects the LiveKit voice agent (running on big-chungus) to the Mac client, enabling voice commands to execute both as text input and intelligent agent actions.

## Architecture

```
Mac Client (SSH Terminal) 
    ↕ WebSocket
LiveKit Agent (big-chungus)
    ↕ MCP Protocol  
MCP Servers (tools/APIs)
```

## Implementation Components

### 1. Agent Bridge Server (big-chungus)
**File**: `agent_bridge.py`

```python
import asyncio
import websockets
import json
from livekit.agents import JobContext
from agent_core import FunctionAgent

class AgentBridge:
    def __init__(self):
        self.clients = set()
        self.agent = None
    
    async def register_client(self, websocket):
        self.clients.add(websocket)
        await websocket.send(json.dumps({"type": "connected"}))
    
    async def handle_voice_result(self, text, agent_response=None):
        """Send results to all connected Mac clients"""
        message = {
            "type": "voice_result",
            "text": text,
            "agent_response": agent_response,
            "timestamp": time.time()
        }
        
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        self.clients -= disconnected

bridge = AgentBridge()
```

### 2. Modified Agent Core (big-chungus)
**File**: `agent_core.py` (modify existing)

Add bridge integration to existing `FunctionAgent`:

```python
# Add to existing FunctionAgent class
async def on_speech_final(self, event):
    """Override to send results to bridge"""
    text = event.alternatives[0].text
    
    # Process with agent (existing logic)
    agent_response = await self.process_command(text)
    
    # Send to bridge
    await bridge.handle_voice_result(text, agent_response)
```

### 3. Mac Client Bridge
**File**: `mac_client.py` (runs on Mac)

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import pyautogui
import argparse
import logging

class MacBridge:
    def __init__(self, server_url, mode="type"):
        self.server_url = server_url
        self.mode = mode  # "type" or "command" or "both"
        
    async def connect(self):
        async with websockets.connect(self.server_url) as websocket:
            print(f"🔗 Connected to {self.server_url}")
            print(f"📝 Mode: {self.mode}")
            
            async for message in websocket:
                await self.handle_message(json.loads(message))
    
    async def handle_message(self, data):
        if data["type"] == "voice_result":
            text = data["text"]
            agent_response = data.get("agent_response")
            
            if self.mode in ["type", "both"]:
                # Type the transcribed text
                pyautogui.typewrite(text)
            
            if self.mode in ["command", "both"] and agent_response:
                # Execute agent command results
                if agent_response.get("action") == "type":
                    pyautogui.typewrite(agent_response["content"])
                elif agent_response.get("action") == "execute":
                    # Could execute local Mac commands
                    print(f"🤖 Agent says: {agent_response['content']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="wss://lk.delo.sh/bridge")
    parser.add_argument("--mode", choices=["type", "command", "both"], default="both")
    args = parser.parse_args()
    
    bridge = MacBridge(args.server, args.mode)
    asyncio.run(bridge.connect())
```

### 4. WebSocket Server Integration (big-chungus)
**File**: `websocket_server.py`

```python
import asyncio
import websockets
import json
from agent_bridge import bridge

async def handle_client(websocket, path):
    if path == "/bridge":
        await bridge.register_client(websocket)
        try:
            await websocket.wait_closed()
        finally:
            bridge.clients.discard(websocket)

# Add to existing compose.yml or run separately
start_server = websockets.serve(handle_client, "0.0.0.0", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
```

### 5. Traefik Configuration (big-chungus)
**File**: `traefik-data/dynamic/livekit-bridge.yml`

```yaml
http:
  routers:
    livekit-bridge:
      rule: "Host(`lk.delo.sh`) && PathPrefix(`/bridge`)"
      entryPoints:
        - websecure
      service: livekit-bridge-service
      tls:
        certResolver: letsencrypt

  services:
    livekit-bridge-service:
      loadBalancer:
        servers:
          - url: "http://livekit-server:8765"
```

## Installation & Setup

### On big-chungus:
```bash
cd /home/delorenj/code/mcp/voice-mcp-agent

# Add WebSocket server to compose.yml
# Modify agent_core.py to include bridge
# Add Traefik config
# Restart services

docker-compose up -d
```

### On Mac:
```bash
# Install dependencies
pip install websockets pyautogui

# Download mac_client.py from big-chungus
scp big-chungus:/home/delorenj/code/mcp/voice-mcp-agent/mac_client.py .

# Run bridge client
python3 mac_client.py --server wss://lk.delo.sh/bridge --mode both
```

## Usage Modes

### 1. Type Mode (`--mode type`)
- Voice → transcribed text typed into active Mac app
- Simple STT replacement

### 2. Command Mode (`--mode command`) 
- Voice → agent processes → intelligent responses
- Agent can execute MCP tools, return structured data

### 3. Both Mode (`--mode both`)
- Transcribed text + agent intelligence
- Best of both worlds

## Testing

1. Start LiveKit agent on big-chungus
2. Run Mac bridge client
3. Speak into LiveKit web interface
4. Verify text appears in Mac terminal/apps

## Security Considerations

- WebSocket connection over WSS (encrypted)
- Limit bridge to specific IP ranges in Traefik
- Add authentication token if needed

## File Structure
```
voice-mcp-agent/
├── agent_bridge.py          # Bridge server
├── websocket_server.py      # WebSocket handler  
├── mac_client.py            # Mac client
├── agent_core.py            # Modified agent
└── traefik-data/dynamic/
    └── livekit-bridge.yml   # Traefik config
```

## Contractor Deliverables

1. **Modified agent_core.py** - Bridge integration
2. **agent_bridge.py** - Bridge server implementation
3. **websocket_server.py** - WebSocket server
4. **mac_client.py** - Mac client application
5. **Traefik configuration** - WebSocket routing
6. **Updated compose.yml** - Include bridge server
7. **Testing documentation** - Verification steps

## Success Criteria

- [ ] Voice input on LiveKit web interface
- [ ] Text appears in Mac terminal via bridge
- [ ] Agent responses execute on Mac
- [ ] Secure WebSocket connection (WSS)
- [ ] Multiple Mac clients can connect
- [ ] Graceful disconnect/reconnect handling
