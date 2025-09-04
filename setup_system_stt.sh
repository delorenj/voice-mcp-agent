#!/bin/bash
# Setup system-wide STT

echo "🎤 Setting up system-wide STT..."

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-tk

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-system.txt

echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  Continuous STT: python3 system_stt_daemon.py"
echo "  Hotkey STT:     python3 hotkey_stt.py"
echo ""
echo "Note: You may need to run with sudo for global hotkeys"
