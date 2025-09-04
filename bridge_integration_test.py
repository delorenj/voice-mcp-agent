#!/usr/bin/env python3
"""
bridge_integration_test.py

Test script to verify the Mac Bridge integration is working correctly.
Tests bridge server, WebSocket connection, and message flow.
"""

import asyncio
import websockets
import json
import logging
import time
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BridgeIntegrationTest:
    """Integration test for Mac Bridge components"""
    
    def __init__(self, server_url: str = "ws://localhost:8765/bridge"):
        self.server_url = server_url
        self.test_results = {}
        
    async def run_all_tests(self):
        """Run all bridge integration tests"""
        logger.info("🧪 Starting Mac Bridge Integration Tests")
        
        tests = [
            ("bridge_import", self._test_bridge_import),
            ("websocket_connection", self._test_websocket_connection),
            ("client_registration", self._test_client_registration),
            ("voice_result_handling", self._test_voice_result_handling),
            ("mode_switching", self._test_mode_switching),
            ("multiple_clients", self._test_multiple_clients),
            ("error_handling", self._test_error_handling)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"🔍 Running test: {test_name}")
            try:
                result = await test_func()
                self.test_results[test_name] = {"passed": True, "result": result}
                logger.info(f"✅ {test_name} PASSED")
            except Exception as e:
                self.test_results[test_name] = {"passed": False, "error": str(e)}
                logger.error(f"❌ {test_name} FAILED: {e}")
        
        self._print_summary()
        return self.test_results
    
    async def _test_bridge_import(self):
        """Test that bridge components can be imported"""
        try:
            from agent_bridge import bridge, AgentBridge, VoiceResult
            from websocket_server import WebSocketServer
            return {"bridge_available": True, "classes_imported": True}
        except ImportError as e:
            raise Exception(f"Failed to import bridge components: {e}")
    
    async def _test_websocket_connection(self):
        """Test WebSocket server connection"""
        try:
            # Try to connect to WebSocket server
            async with websockets.connect(
                self.server_url,
                ping_timeout=5,
                close_timeout=5
            ) as websocket:
                # Send ping
                ping_message = {"type": "ping", "timestamp": time.time()}
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                return {
                    "connected": True,
                    "ping_response": data.get("type") in ["pong", "connected"]
                }
        except Exception as e:
            raise Exception(f"WebSocket connection failed: {e}")
    
    async def _test_client_registration(self):
        """Test client registration process"""
        async with websockets.connect(f"{self.server_url}?mode=both") as websocket:
            # Wait for connection message
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("type") != "connected":
                raise Exception(f"Expected 'connected' message, got: {data}")
            
            client_id = data.get("client_id")
            if not client_id:
                raise Exception("No client_id in connection response")
            
            return {
                "registered": True,
                "client_id": client_id,
                "mode": data.get("mode", "unknown")
            }
    
    async def _test_voice_result_handling(self):
        """Test voice result message handling"""
        # Import bridge after ensuring it's available
        from agent_bridge import bridge
        
        async with websockets.connect(f"{self.server_url}?mode=both") as websocket:
            # Wait for connection
            await websocket.recv()
            
            # Simulate voice result from agent
            test_text = "Hello, this is a test message"
            test_response = {
                "action": "type",
                "content": "Test agent response",
                "params": {}
            }
            
            # Send voice result through bridge
            await bridge.handle_agent_response(test_text, test_response)
            
            # Wait for message
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("type") != "voice_result":
                raise Exception(f"Expected 'voice_result' message, got: {data}")
            
            return {
                "message_received": True,
                "text_matches": data.get("text") == test_text,
                "has_agent_response": "agent_response" in data
            }
    
    async def _test_mode_switching(self):
        """Test client mode switching"""
        async with websockets.connect(f"{self.server_url}?mode=type") as websocket:
            # Wait for connection
            await websocket.recv()
            
            # Request mode change
            mode_change = {"type": "mode_change", "mode": "command"}
            await websocket.send(json.dumps(mode_change))
            
            # Wait for confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("type") != "mode_changed":
                raise Exception(f"Expected 'mode_changed' message, got: {data}")
            
            return {
                "mode_changed": True,
                "new_mode": data.get("new_mode")
            }
    
    async def _test_multiple_clients(self):
        """Test multiple client connections"""
        clients = []
        client_ids = []
        
        try:
            # Connect multiple clients
            for i in range(3):
                websocket = await websockets.connect(f"{self.server_url}?mode=both")
                clients.append(websocket)
                
                # Wait for connection message
                response = await websocket.recv()
                data = json.loads(response)
                client_ids.append(data.get("client_id"))
            
            # Test broadcast functionality
            from agent_bridge import bridge
            
            # Get client count before
            initial_count = bridge.get_client_count()
            
            # Send a message
            await bridge.handle_simple_text("Broadcast test message")
            
            # Check that all clients receive the message
            received_count = 0
            for websocket in clients:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    if data.get("type") == "voice_result":
                        received_count += 1
                except asyncio.TimeoutError:
                    pass
            
            return {
                "clients_connected": len(clients),
                "unique_client_ids": len(set(client_ids)),
                "bridge_client_count": initial_count,
                "broadcast_received": received_count
            }
        
        finally:
            # Clean up connections
            for websocket in clients:
                try:
                    await websocket.close()
                except:
                    pass
    
    async def _test_error_handling(self):
        """Test error handling scenarios"""
        # Test invalid mode
        async with websockets.connect(f"{self.server_url}?mode=invalid") as websocket:
            # Should still connect but with default mode
            response = await websocket.recv()
            data = json.loads(response)
            
            # Test invalid message
            invalid_message = {"type": "invalid_type", "data": "test"}
            await websocket.send(json.dumps(invalid_message))
            
            # Should not cause disconnection
            await asyncio.sleep(1)
            
            # Test ping to ensure connection is still alive
            ping = {"type": "ping", "timestamp": time.time()}
            await websocket.send(json.dumps(ping))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            return {
                "handles_invalid_mode": True,
                "handles_invalid_message": True,
                "connection_stable": data.get("type") in ["pong", "connected"]
            }
    
    def _print_summary(self):
        """Print test summary"""
        passed_count = sum(1 for result in self.test_results.values() if result["passed"])
        total_count = len(self.test_results)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Mac Bridge Integration Test Summary")
        logger.info(f"{'='*50}")
        logger.info(f"Tests passed: {passed_count}/{total_count}")
        
        if passed_count == total_count:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.warning(f"⚠️  {total_count - passed_count} tests failed")
            
            for test_name, result in self.test_results.items():
                if not result["passed"]:
                    logger.error(f"❌ {test_name}: {result['error']}")
        
        logger.info(f"{'='*50}")

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mac Bridge Integration Tests")
    parser.add_argument("--server", default="ws://localhost:8765/bridge", 
                       help="Bridge server WebSocket URL")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Wait a bit for server to start if needed
    await asyncio.sleep(1)
    
    tester = BridgeIntegrationTest(args.server)
    results = await tester.run_all_tests()
    
    # Exit with error code if tests failed
    if not all(result["passed"] for result in results.values()):
        exit(1)
    
    logger.info("✅ All integration tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())