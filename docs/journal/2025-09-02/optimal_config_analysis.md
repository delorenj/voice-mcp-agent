# Optimal Voice-MCP-Agent Configuration for big-chungus

## Current Situation Analysis
- **Server**: big-chungus (192.168.1.12) - Main server running voice-mcp-agent
- **Client**: mommymac (remote SSH) - User workstation with microphone
- **Network**: Same home network
- **MCP Servers**: HTTP proxy aggregated on big-chungus
- **Challenge**: Audio input from remote client to server-hosted agent

## Solution Options

### Option 1: LiveKit Cloud + Self-Hosted STT (RECOMMENDED)
**Architecture**: Use LiveKit Cloud for audio routing, local Whisper for STT

**Advantages:**
- Real-time audio streaming from any device
- Professional WebRTC handling
- Self-hosted STT processing
- Web browser access from mommymac
- No complex local audio routing

**Implementation:**
1. Replace OpenAI STT with local Whisper
2. Keep LiveKit Cloud for audio routing
3. Access via web browser on mommymac

### Option 2: Full Self-Hosted with Audio Tunneling
**Architecture**: Self-hosted LiveKit + audio tunneling via SSH

**Advantages:**
- Complete self-hosted solution
- No external dependencies

**Disadvantages:**
- Complex audio routing setup
- SSH audio tunneling latency
- LiveKit server setup required

### Option 3: Hybrid HTTP API + Local Whisper
**Architecture**: HTTP API on big-chungus with browser audio capture

**Advantages:**
- Simpler setup
- Direct HTTP communication
- Browser-based audio capture

**Disadvantages:**
- No real-time conversation flow
- Manual audio recording/uploading

## RECOMMENDED IMPLEMENTATION

### Step 1: Add Local Whisper STT
Replace OpenAI STT with local Whisper in agent_core.py:

```python
# Current (OpenAI STT)
stt=openai.STT(),

# Replace with local Whisper
stt=whisper.STT(model="base"),  # or "small", "medium", "large"
```

### Step 2: LiveKit Cloud Configuration
Set up LiveKit Cloud project for audio routing:
- Creates real-time audio connection
- Handles WebRTC complexities
- Provides web interface for mommymac

### Step 3: Access Configuration
From mommymac:
1. Open web browser to LiveKit room URL
2. Grant microphone permissions
3. Talk directly to big-chungus hosted agent

## Required Changes

### Dependencies Update
Add to requirements.txt:
```
livekit-plugins-whisper>=1.0.0
faster-whisper>=1.0.0
```

### Agent Configuration Update
```python
from livekit.plugins import whisper

# In agent_core.py FunctionAgent.__init__():
stt=whisper.STT(model="base", language="en"),
```

### Environment Variables
```bash
# On big-chungus
export LIVEKIT_URL="wss://your-project.livekit.cloud"
export LIVEKIT_API_KEY="your-api-key"
export LIVEKIT_API_SECRET="your-api-secret"
```

## Network Configuration
- big-chungus serves as agent host (192.168.1.12)
- mommymac connects via browser to LiveKit Cloud
- Audio flows: mommymac → LiveKit Cloud → big-chungus
- Responses flow: big-chungus → LiveKit Cloud → mommymac

## Performance Optimization
- Use Whisper "base" model for speed vs accuracy balance
- Consider GPU acceleration if available on big-chungus
- Monitor CPU usage during STT processing

## Security Considerations
- LiveKit Cloud handles encrypted WebRTC streams
- MCP servers remain local to big-chungus network
- No sensitive data leaves your network except audio streams

## Cost Analysis
- LiveKit Cloud: Pay-per-use pricing (~$0.40/hour active usage)
- Whisper STT: Free (local processing)
- Overall: Much cheaper than OpenAI STT for regular usage