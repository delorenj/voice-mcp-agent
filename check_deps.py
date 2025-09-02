#!/usr/bin/env python3
"""
Dependency verification script for LiveKit Voice MCP Agent
"""

def check_dependencies():
    """Check if all required packages can be imported correctly"""
    
    import_tests = [
        ('livekit-agents', 'livekit.agents'),
        ('livekit-plugins-openai', 'livekit.plugins.openai'),
        ('livekit-plugins-elevenlabs', 'livekit.plugins.elevenlabs'),  
        ('livekit-plugins-silero', 'livekit.plugins.silero'),
        ('mcp', 'mcp'),
        ('faster-whisper', 'faster_whisper'),
        ('pytest', 'pytest')
    ]
    
    missing = []
    success_count = 0
    
    for pkg_name, import_name in import_tests:
        try:
            __import__(import_name)
            print(f'✓ {pkg_name}')
            success_count += 1
        except ImportError as e:
            missing.append(pkg_name)
            print(f'✗ {pkg_name} - Import Error: {e}')
    
    print(f'\nSUMMARY: {success_count}/{len(import_tests)} packages successfully imported')
    
    if missing:
        print(f'❌ Missing packages: {missing}')
        return False
    else:
        print('✅ All dependencies satisfied!')
        return True

if __name__ == '__main__':
    import sys
    if not check_dependencies():
        sys.exit(1)