"""
websocket_server.py

WebSocket server that handles Mac client connections for the LiveKit bridge.
Integrates with the agent_bridge to manage client registration and message routing.
"""

import asyncio
import websockets
import json
import logging
import signal
import sys
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

from agent_bridge import bridge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for Mac client connections"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        
    async def handle_client_connection(self, websocket: websockets.WebSocketServerProtocol, 
                                     path: str):
        """
        Handle new client WebSocket connection
        
        Args:
            websocket: WebSocket connection
            path: Connection path (should be /bridge)
        """
        # Parse connection parameters
        parsed_url = urlparse(path)
        query_params = parse_qs(parsed_url.query)
        
        # Extract mode from query parameters (default: "both")
        mode = query_params.get('mode', ['both'])[0]
        if mode not in ['type', 'command', 'both']:
            logger.warning(f"Invalid mode '{mode}', defaulting to 'both'")
            mode = 'both'
        
        client_id = None
        
        try:
            # Register client with bridge
            client_id = await bridge.register_client(websocket, mode)
            
            logger.info(f"New client connection from {websocket.remote_address} "
                       f"with client_id {client_id} and mode '{mode}'")
            
            # Keep connection alive and handle any incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(client_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from client {client_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed normally")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"Client {client_id} connection closed with error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error handling client {client_id}: {e}")
        finally:
            # Ensure client is unregistered
            if client_id:
                await bridge.unregister_client(client_id)
                logger.info(f"Client {client_id} cleanup completed")
    
    async def handle_client_message(self, client_id: str, data: Dict[str, Any]):
        """
        Handle incoming message from Mac client
        
        Args:
            client_id: Client identifier
            data: Message data
        """
        message_type = data.get('type', 'unknown')
        
        if message_type == 'ping':
            # Respond to ping with pong
            await bridge.send_to_client(client_id, {
                "type": "pong",
                "timestamp": data.get('timestamp'),
                "server_timestamp": asyncio.get_event_loop().time()
            })
            
        elif message_type == 'status_request':
            # Send status information
            client_info = bridge.get_client_info()
            await bridge.send_to_client(client_id, {
                "type": "status_response",
                "client_count": len(client_info),
                "clients": client_info,
                "timestamp": asyncio.get_event_loop().time()
            })
            
        elif message_type == 'mode_change':
            # Handle mode change request
            new_mode = data.get('mode', 'both')
            if new_mode in ['type', 'command', 'both']:
                # Update client mode
                if client_id in bridge.clients:
                    bridge.clients[client_id].mode = new_mode
                    await bridge.send_to_client(client_id, {
                        "type": "mode_changed",
                        "new_mode": new_mode,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    logger.info(f"Client {client_id} changed mode to '{new_mode}'")
            else:
                await bridge.send_to_client(client_id, {
                    "type": "error",
                    "message": f"Invalid mode: {new_mode}",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
        else:
            logger.warning(f"Unknown message type '{message_type}' from client {client_id}")
    
    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        # Create server for /bridge path
        async def route_handler(websocket, path):
            if path.startswith('/bridge'):
                await self.handle_client_connection(websocket, path)
            else:
                # Close connection for invalid paths
                await websocket.close(code=1000, reason="Invalid path")
        
        self.server = await websockets.serve(
            route_handler,
            self.host,
            self.port,
            ping_interval=30,  # Send ping every 30 seconds
            ping_timeout=10,   # Wait 10 seconds for pong
            close_timeout=10,  # Wait 10 seconds when closing
            max_size=1024*1024,  # 1MB max message size
        )
        
        logger.info(f"WebSocket bridge server started on {self.host}:{self.port}")
        logger.info(f"Clients should connect to: ws://{self.host}:{self.port}/bridge")
        
        # Send periodic status updates
        asyncio.create_task(self.status_update_task())
        
        await self.server.wait_closed()
    
    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.running = False
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket bridge server stopped")
    
    async def status_update_task(self):
        """Periodic status update task"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Send status every minute
                if bridge.get_client_count() > 0:
                    await bridge.send_status_update()
            except Exception as e:
                logger.error(f"Error in status update task: {e}")

# Global server instance
websocket_server = WebSocketServer()

async def start_websocket_server(host: str = "0.0.0.0", port: int = 8765):
    """Start WebSocket server - convenience function"""
    global websocket_server
    websocket_server = WebSocketServer(host, port)
    await websocket_server.start()

def setup_signal_handlers():
    """Setup graceful shutdown signal handlers"""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(websocket_server.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LiveKit Mac Bridge WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    try:
        asyncio.run(start_websocket_server(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)