"""
agent_bridge.py

Bridge server that connects LiveKit voice agent to Mac clients via WebSocket.
Manages client connections and handles voice recognition results distribution.
"""

import asyncio
import websockets
import json
import logging
import time
import weakref
from typing import Set, Dict, Any, Optional
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VoiceResult:
    """Structured voice recognition result"""
    text: str
    agent_response: Optional[Dict[str, Any]] = None
    timestamp: float = None
    confidence: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class ClientInfo:
    """Information about connected Mac clients"""
    websocket: websockets.WebSocketServerProtocol
    connected_at: float
    client_id: str
    mode: str = "both"  # "type", "command", or "both"
    
    def __post_init__(self):
        if not hasattr(self, 'connected_at'):
            self.connected_at = time.time()

class AgentBridge:
    """
    Bridge server that manages WebSocket connections to Mac clients
    and distributes voice recognition results from the LiveKit agent.
    """
    
    def __init__(self):
        self.clients: Dict[str, ClientInfo] = {}
        self.agent = None
        self._client_counter = 0
        
    def generate_client_id(self) -> str:
        """Generate unique client identifier"""
        self._client_counter += 1
        return f"mac_client_{self._client_counter}_{int(time.time())}"
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol, 
                            mode: str = "both") -> str:
        """
        Register a new Mac client connection
        
        Args:
            websocket: WebSocket connection
            mode: Operation mode ("type", "command", "both")
            
        Returns:
            Generated client ID
        """
        client_id = self.generate_client_id()
        
        client_info = ClientInfo(
            websocket=websocket,
            connected_at=time.time(),
            client_id=client_id,
            mode=mode
        )
        
        self.clients[client_id] = client_info
        
        # Send connection confirmation
        await self.send_to_client(client_id, {
            "type": "connected",
            "client_id": client_id,
            "mode": mode,
            "server_time": time.time()
        })
        
        logger.info(f"Client {client_id} registered with mode '{mode}'. "
                   f"Total clients: {len(self.clients)}")
        
        return client_id
    
    async def unregister_client(self, client_id: str):
        """Remove client from registry"""
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Client {client_id} unregistered. "
                       f"Remaining clients: {len(self.clients)}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific client
        
        Returns:
            True if sent successfully, False if client disconnected
        """
        if client_id not in self.clients:
            return False
            
        client = self.clients[client_id]
        try:
            await client.websocket.send(json.dumps(message))
            return True
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.ConnectionClosedError):
            logger.warning(f"Client {client_id} connection closed during send")
            await self.unregister_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            return False
    
    async def broadcast_to_clients(self, message: Dict[str, Any], 
                                 mode_filter: Optional[str] = None) -> int:
        """
        Broadcast message to all clients, optionally filtering by mode
        
        Args:
            message: Message to broadcast
            mode_filter: Only send to clients with this mode (None for all)
            
        Returns:
            Number of clients that received the message
        """
        disconnected_clients = []
        sent_count = 0
        
        for client_id, client_info in self.clients.items():
            # Apply mode filter if specified
            if mode_filter and client_info.mode not in [mode_filter, "both"]:
                continue
                
            success = await self.send_to_client(client_id, message)
            if success:
                sent_count += 1
            else:
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.unregister_client(client_id)
        
        return sent_count
    
    async def handle_voice_result(self, voice_result: VoiceResult):
        """
        Process and distribute voice recognition results to Mac clients
        
        Args:
            voice_result: Voice recognition result with text and optional agent response
        """
        message = {
            "type": "voice_result",
            **asdict(voice_result)
        }
        
        # Determine appropriate clients based on content
        mode_filter = None
        if voice_result.agent_response:
            # If we have agent response, send to command-enabled clients
            mode_filter = "command"
        
        sent_count = await self.broadcast_to_clients(message, mode_filter)
        
        logger.info(f"Voice result distributed to {sent_count} clients: "
                   f"'{voice_result.text[:50]}{'...' if len(voice_result.text) > 50 else ''}'")
    
    async def handle_agent_response(self, text: str, agent_response: Dict[str, Any]):
        """
        Handle agent response with structured data
        
        Args:
            text: Original transcribed text
            agent_response: Structured response from agent
        """
        voice_result = VoiceResult(
            text=text,
            agent_response=agent_response,
            timestamp=time.time()
        )
        
        await self.handle_voice_result(voice_result)
    
    async def handle_simple_text(self, text: str, confidence: Optional[float] = None):
        """
        Handle simple text transcription without agent processing
        
        Args:
            text: Transcribed text
            confidence: Recognition confidence score
        """
        voice_result = VoiceResult(
            text=text,
            confidence=confidence,
            timestamp=time.time()
        )
        
        await self.handle_voice_result(voice_result)
    
    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.clients)
    
    def get_client_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all connected clients"""
        return {
            client_id: {
                "client_id": client_info.client_id,
                "mode": client_info.mode,
                "connected_at": client_info.connected_at,
                "connected_for": time.time() - client_info.connected_at
            }
            for client_id, client_info in self.clients.items()
        }
    
    async def send_status_update(self):
        """Send status update to all clients"""
        status_message = {
            "type": "status_update",
            "connected_clients": len(self.clients),
            "server_uptime": time.time(),
            "timestamp": time.time()
        }
        
        await self.broadcast_to_clients(status_message)

# Global bridge instance
bridge = AgentBridge()

# Convenience functions for integration
async def register_client(websocket: websockets.WebSocketServerProtocol, 
                         mode: str = "both") -> str:
    """Register new client - convenience function"""
    return await bridge.register_client(websocket, mode)

async def handle_voice_result(text: str, agent_response: Optional[Dict[str, Any]] = None, 
                            confidence: Optional[float] = None):
    """Handle voice result - convenience function"""
    if agent_response:
        await bridge.handle_agent_response(text, agent_response)
    else:
        await bridge.handle_simple_text(text, confidence)

def get_client_count() -> int:
    """Get client count - convenience function"""
    return bridge.get_client_count()