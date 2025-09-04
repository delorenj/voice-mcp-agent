#!/usr/bin/env python3
"""
mac_client.py

Mac client application that connects to the LiveKit bridge via WebSocket
and executes voice recognition results using pyautogui for typing and system automation.
"""

import asyncio
import websockets
import json
import logging
import argparse
import sys
import time
import signal
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    # Configure pyautogui safety
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1  # Small pause between actions
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️  pyautogui not available. Install with: pip install pyautogui")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MacClientConfig:
    """Configuration for Mac client"""
    server_url: str
    mode: str = "both"  # "type", "command", or "both"
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    ping_interval: int = 30
    typing_delay: float = 0.01  # Delay between keystrokes
    safety_mode: bool = True  # Enable additional safety checks

class MacBridgeClient:
    """
    Mac client that connects to LiveKit bridge and executes voice commands
    """
    
    def __init__(self, config: MacClientConfig):
        self.config = config
        self.websocket = None
        self.client_id = None
        self.connected = False
        self.running = False
        self.last_ping = 0
        self.connection_start_time = 0
        
        # Action handlers
        self.action_handlers = {
            'type': self._handle_type_action,
            'execute': self._handle_execute_action,
            'click': self._handle_click_action,
            'key': self._handle_key_action,
            'move': self._handle_move_action
        }
        
        if not PYAUTOGUI_AVAILABLE:
            logger.warning("PyAutoGUI not available - typing functionality disabled")
    
    async def connect(self):
        """Connect to the bridge server"""
        self.running = True
        
        while self.running:
            try:
                await self._connect_to_server()
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                
                if not self.config.auto_reconnect:
                    break
                    
                logger.info(f"Reconnecting in {self.config.reconnect_delay} seconds...")
                await asyncio.sleep(self.config.reconnect_delay)
    
    async def _connect_to_server(self):
        """Establish WebSocket connection to server"""
        # Add mode parameter to URL
        url_with_params = f"{self.config.server_url}?mode={self.config.mode}"
        
        logger.info(f"Connecting to {url_with_params}")
        
        async with websockets.connect(
            url_with_params,
            ping_interval=self.config.ping_interval,
            ping_timeout=10,
            close_timeout=10
        ) as websocket:
            self.websocket = websocket
            self.connected = True
            self.connection_start_time = time.time()
            
            logger.info(f"🔗 Connected to bridge server")
            logger.info(f"📝 Mode: {self.config.mode}")
            logger.info(f"🔄 Auto-reconnect: {self.config.auto_reconnect}")
            logger.info(f"🛡️  Safety mode: {self.config.safety_mode}")
            
            # Start ping task
            ping_task = asyncio.create_task(self._ping_task())
            
            try:
                # Handle incoming messages
                async for message in websocket:
                    await self._handle_message(json.loads(message))
                    
            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed by server")
            finally:
                self.connected = False
                self.websocket = None
                ping_task.cancel()
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'connected':
            self.client_id = data.get('client_id')
            logger.info(f"✅ Registered as client {self.client_id}")
            
        elif message_type == 'voice_result':
            await self._handle_voice_result(data)
            
        elif message_type == 'status_update':
            logger.debug(f"Server status: {data.get('connected_clients', 0)} clients")
            
        elif message_type == 'pong':
            logger.debug("Pong received")
            
        elif message_type == 'mode_changed':
            self.config.mode = data.get('new_mode', self.config.mode)
            logger.info(f"Mode changed to: {self.config.mode}")
            
        elif message_type == 'error':
            logger.error(f"Server error: {data.get('message', 'Unknown error')}")
            
        else:
            logger.debug(f"Received unknown message type: {message_type}")
    
    async def _handle_voice_result(self, data: Dict[str, Any]):
        """Handle voice recognition result"""
        text = data.get('text', '')
        agent_response = data.get('agent_response')
        timestamp = data.get('timestamp', time.time())
        confidence = data.get('confidence')
        
        logger.info(f"🎤 Voice input: '{text}'")
        if confidence:
            logger.info(f"   Confidence: {confidence:.2f}")
        
        # Process based on mode
        if self.config.mode in ['type', 'both'] and text:
            await self._type_text(text)
        
        if self.config.mode in ['command', 'both'] and agent_response:
            await self._execute_agent_response(agent_response)
    
    async def _type_text(self, text: str):
        """Type text using pyautogui"""
        if not PYAUTOGUI_AVAILABLE:
            logger.warning("Cannot type - pyautogui not available")
            return
        
        if self.config.safety_mode and len(text) > 1000:
            logger.warning("Text too long (>1000 chars), skipping for safety")
            return
        
        try:
            logger.info(f"⌨️  Typing: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Type with small delay between characters
            pyautogui.typewrite(text, interval=self.config.typing_delay)
            
        except Exception as e:
            logger.error(f"Error typing text: {e}")
    
    async def _execute_agent_response(self, response: Dict[str, Any]):
        """Execute structured agent response"""
        action = response.get('action', 'unknown')
        content = response.get('content', '')
        params = response.get('params', {})
        
        logger.info(f"🤖 Agent action: {action}")
        
        if action in self.action_handlers:
            try:
                await self.action_handlers[action](content, params)
            except Exception as e:
                logger.error(f"Error executing action '{action}': {e}")
        else:
            logger.warning(f"Unknown agent action: {action}")
            # Fallback: just type the content
            if content:
                await self._type_text(content)
    
    async def _handle_type_action(self, content: str, params: Dict[str, Any]):
        """Handle type action from agent"""
        await self._type_text(content)
    
    async def _handle_execute_action(self, content: str, params: Dict[str, Any]):
        """Handle execute action from agent"""
        logger.info(f"🔧 Execute: {content}")
        # For now, just log the command - could execute shell commands if needed
        print(f"Would execute: {content}")
    
    async def _handle_click_action(self, content: str, params: Dict[str, Any]):
        """Handle click action from agent"""
        if not PYAUTOGUI_AVAILABLE:
            return
        
        x = params.get('x')
        y = params.get('y')
        button = params.get('button', 'left')
        
        if x is not None and y is not None:
            logger.info(f"🖱️  Clicking at ({x}, {y}) with {button} button")
            pyautogui.click(x, y, button=button)
        else:
            logger.warning("Click action missing coordinates")
    
    async def _handle_key_action(self, content: str, params: Dict[str, Any]):
        """Handle key press action from agent"""
        if not PYAUTOGUI_AVAILABLE:
            return
        
        key = params.get('key', content)
        if key:
            logger.info(f"⌨️  Pressing key: {key}")
            pyautogui.press(key)
    
    async def _handle_move_action(self, content: str, params: Dict[str, Any]):
        """Handle mouse move action from agent"""
        if not PYAUTOGUI_AVAILABLE:
            return
        
        x = params.get('x')
        y = params.get('y')
        
        if x is not None and y is not None:
            logger.info(f"🖱️  Moving mouse to ({x}, {y})")
            pyautogui.moveTo(x, y)
    
    async def _ping_task(self):
        """Send periodic pings to keep connection alive"""
        while self.connected and self.websocket:
            try:
                await asyncio.sleep(self.config.ping_interval)
                
                ping_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                
                await self.websocket.send(json.dumps(ping_message))
                self.last_ping = time.time()
                
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                break
    
    async def change_mode(self, new_mode: str):
        """Change client mode"""
        if new_mode not in ['type', 'command', 'both']:
            logger.error(f"Invalid mode: {new_mode}")
            return
        
        if self.websocket and self.connected:
            message = {
                "type": "mode_change",
                "mode": new_mode
            }
            
            await self.websocket.send(json.dumps(message))
        else:
            logger.warning("Not connected - mode change will apply on next connection")
            self.config.mode = new_mode
    
    async def request_status(self):
        """Request status from server"""
        if self.websocket and self.connected:
            message = {
                "type": "status_request",
                "timestamp": time.time()
            }
            
            await self.websocket.send(json.dumps(message))
    
    def stop(self):
        """Stop the client"""
        self.running = False
        logger.info("Stopping Mac bridge client...")

def setup_signal_handlers(client: MacBridgeClient):
    """Setup graceful shutdown signal handlers"""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def interactive_mode(client: MacBridgeClient):
    """Interactive mode for testing and control"""
    print("\n🎮 Interactive mode - Available commands:")
    print("  mode <type|command|both> - Change mode")
    print("  status - Request server status")
    print("  quit - Exit")
    print()
    
    while client.running:
        try:
            command = input("mac-bridge> ").strip().lower()
            
            if command.startswith("mode "):
                new_mode = command.split(" ", 1)[1]
                await client.change_mode(new_mode)
                
            elif command == "status":
                await client.request_status()
                
            elif command in ["quit", "exit"]:
                client.stop()
                break
                
            else:
                print("Unknown command")
                
        except EOFError:
            client.stop()
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LiveKit Mac Bridge Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect with both typing and command execution
  python3 mac_client.py --server wss://lk.delo.sh/bridge --mode both
  
  # Only type transcribed text
  python3 mac_client.py --server ws://localhost:8765/bridge --mode type
  
  # Only execute agent commands
  python3 mac_client.py --mode command --no-safety
        """
    )
    
    parser.add_argument(
        "--server", 
        default="ws://localhost:8765/bridge",
        help="Bridge server WebSocket URL"
    )
    parser.add_argument(
        "--mode", 
        choices=["type", "command", "both"], 
        default="both",
        help="Operation mode"
    )
    parser.add_argument(
        "--no-reconnect", 
        action="store_true",
        help="Disable auto-reconnect"
    )
    parser.add_argument(
        "--reconnect-delay", 
        type=int, 
        default=5,
        help="Reconnection delay in seconds"
    )
    parser.add_argument(
        "--typing-delay", 
        type=float, 
        default=0.01,
        help="Delay between keystrokes"
    )
    parser.add_argument(
        "--no-safety", 
        action="store_true",
        help="Disable safety mode"
    )
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="Enable interactive mode"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check pyautogui availability
    if not PYAUTOGUI_AVAILABLE and args.mode in ['type', 'both']:
        print("❌ PyAutoGUI required for typing mode. Install with:")
        print("   pip install pyautogui")
        sys.exit(1)
    
    # Create config
    config = MacClientConfig(
        server_url=args.server,
        mode=args.mode,
        auto_reconnect=not args.no_reconnect,
        reconnect_delay=args.reconnect_delay,
        typing_delay=args.typing_delay,
        safety_mode=not args.no_safety
    )
    
    # Create client
    client = MacBridgeClient(config)
    
    # Setup signal handlers
    setup_signal_handlers(client)
    
    try:
        if args.interactive:
            # Run interactive mode with connection in background
            connection_task = asyncio.create_task(client.connect())
            interactive_task = asyncio.create_task(interactive_mode(client))
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [connection_task, interactive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
        else:
            # Run in connection mode
            await client.connect()
            
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {e}")
        sys.exit(1)