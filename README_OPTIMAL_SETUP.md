# Optimal Voice-MCP-Agent Setup for big-chungus + mommymac

## Architecture Overview
- **big-chungus** (192.168.1.12): Hosts voice agent + self-hosted Whisper STT + MCP proxy
- **mommymac**: Connects via web browser to LiveKit Cloud for audio streaming
- **LiveKit Cloud**: Handles WebRTC audio routing between devices
- **Audio Flow**: mommymac → LiveKit Cloud → big-chungus → Self-hosted Whisper

## Setup Instructions

### 1. LiveKit Cloud Setup
1. Create account at [livekit.io](https://livekit.io)
2. Create a new project
3. Copy your project credentials:
   - WebSocket URL (`wss://your-project.livekit.cloud`)
   - API Key
   - API Secret

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your LiveKit credentials
```

### 3. Install Dependencies
```bash
make install
# OR manually:
.venv/bin/pip install -r requirements.txt
```

### 4. Run the Agent
```bash
# On big-chungus
make run
```

### 5. Connect from mommymac
1. The agent will display a LiveKit room URL
2. Open this URL in Safari/Chrome on mommymac
3. Grant microphone permissions
4. Start talking to your voice agent!

## Key Benefits

✅ **Self-Hosted STT**: Whisper runs locally on big-chungus - no OpenAI costs
✅ **Remote Audio**: Easy browser access from any device on your network
✅ **MCP Integration**: All your existing MCP servers work unchanged  
✅ **Low Latency**: WebRTC provides real-time audio streaming
✅ **Cost Effective**: Only LiveKit Cloud usage costs (~$0.40/hour active)

## Performance Tuning

### Whisper Model Selection
- `base`: Fastest, good for simple commands
- `small`: Balanced speed/accuracy
- `medium`: Better accuracy, slower
- `large`: Best accuracy, requires more CPU

Change in `agent_core.py`:
```python
stt=whisper.STT(model="small", language="en")
```

### GPU Acceleration (Optional)
If big-chungus has GPU:
```bash
# Install CUDA-enabled PyTorch first, then:
.venv/bin/pip install faster-whisper[gpu]
```

## Troubleshooting

### Audio Issues
- Ensure microphone permissions in browser
- Check LiveKit room connection status
- Verify WebRTC is not blocked by firewall

### STT Performance
- Monitor CPU usage during transcription
- Consider smaller Whisper model if lag occurs
- Ensure sufficient RAM for chosen model

### MCP Connection
- Verify mcp_servers.yaml configuration
- Check MCP proxy is accessible on big-chungus
- Test MCP endpoints independently

## Network Requirements
- **big-chungus**: Outbound HTTPS (443) to LiveKit Cloud
- **mommymac**: Outbound HTTPS (443) + WebRTC ports to LiveKit Cloud
- **Internal**: MCP proxy accessible on big-chungus network interfaces

## Security Notes
- Audio streams are encrypted via WebRTC
- Speech processing happens locally on big-chungus
- Only audio data leaves your network (to LiveKit Cloud)
- MCP servers remain completely local