#!/usr/bin/env python3
"""
Mac Bridge Integration Tests
Comprehensive integration testing for Mac Bridge WebSocket connections and voice pipeline
"""

import asyncio
import json
import logging
import pytest
import websockets
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch
import soundfile as sf
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacBridgeIntegrationTester:
    """Integration tester for Mac Bridge WebSocket connections"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.websocket_url = config.get('websocket_url', 'wss://localhost:443/ws')
        self.test_results: List[Dict] = []
        self.active_connections: List[websockets.WebSocketServerProtocol] = []
        
    async def create_websocket_connection(self, client_id: str = "test_client") -> websockets.WebSocketClientProtocol:
        """Create a WebSocket connection to the Mac Bridge server"""
        try:
            headers = {
                'User-Agent': f'Mac-STT-Client/{client_id}',
                'X-Client-Type': 'mac_stt',
                'X-Client-Version': '1.0.0'
            }
            
            connection = await websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.active_connections.append(connection)
            logger.info(f"WebSocket connection established for client {client_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create WebSocket connection for {client_id}: {e}")
            raise
    
    async def test_single_client_connection(self) -> Dict[str, Any]:
        """Test single Mac client WebSocket connection"""
        test_start = time.time()
        test_result = {
            'test_name': 'single_client_connection',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        try:
            # Test connection establishment
            connection = await self.create_websocket_connection("single_test")
            
            # Test ping-pong
            await connection.ping()
            
            # Test message sending
            test_message = {
                'type': 'voice_data',
                'client_id': 'single_test',
                'timestamp': time.time(),
                'data': 'test_audio_data_placeholder'
            }
            
            await connection.send(json.dumps(test_message))
            
            # Wait for response
            response = await asyncio.wait_for(connection.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            test_result.update({
                'success': True,
                'details': {
                    'connection_time': time.time() - test_start,
                    'ping_successful': True,
                    'message_sent': True,
                    'response_received': True,
                    'response_data': response_data
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Single client connection test failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_multiple_client_connections(self, num_clients: int = 5) -> Dict[str, Any]:
        """Test multiple concurrent Mac client connections"""
        test_start = time.time()
        test_result = {
            'test_name': 'multiple_client_connections',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {'num_clients': num_clients, 'connections': []}
        }
        
        connections = []
        
        try:
            # Create multiple connections concurrently
            connection_tasks = [
                self.create_websocket_connection(f"client_{i}")
                for i in range(num_clients)
            ]
            
            connections = await asyncio.gather(*connection_tasks)
            logger.info(f"Created {len(connections)} concurrent connections")
            
            # Test simultaneous message sending
            message_tasks = []
            for i, conn in enumerate(connections):
                test_message = {
                    'type': 'voice_data',
                    'client_id': f'client_{i}',
                    'timestamp': time.time(),
                    'data': f'test_audio_data_{i}'
                }
                message_tasks.append(conn.send(json.dumps(test_message)))
            
            await asyncio.gather(*message_tasks)
            logger.info(f"Sent messages from {len(connections)} clients")
            
            # Wait for responses
            response_tasks = [
                asyncio.wait_for(conn.recv(), timeout=10.0)
                for conn in connections
            ]
            
            responses = await asyncio.gather(*response_tasks, return_exceptions=True)
            
            successful_responses = [
                r for r in responses 
                if not isinstance(r, Exception)
            ]
            
            test_result.update({
                'success': len(successful_responses) == num_clients,
                'details': {
                    'connections_created': len(connections),
                    'messages_sent': len(connections),
                    'responses_received': len(successful_responses),
                    'success_rate': len(successful_responses) / num_clients * 100
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Multiple client connection test failed: {e}")
        
        finally:
            # Close all connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_connection_recovery(self) -> Dict[str, Any]:
        """Test connection recovery after network issues"""
        test_start = time.time()
        test_result = {
            'test_name': 'connection_recovery',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        connection = None
        
        try:
            # Establish initial connection
            connection = await self.create_websocket_connection("recovery_test")
            
            # Send initial message
            initial_message = {
                'type': 'voice_data',
                'client_id': 'recovery_test',
                'timestamp': time.time(),
                'data': 'initial_test_data'
            }
            await connection.send(json.dumps(initial_message))
            initial_response = await connection.recv()
            
            # Simulate network disconnection by closing connection
            await connection.close()
            logger.info("Simulated network disconnection")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Attempt reconnection
            connection = await self.create_websocket_connection("recovery_test_reconnect")
            
            # Test functionality after reconnection
            recovery_message = {
                'type': 'voice_data',
                'client_id': 'recovery_test_reconnect',
                'timestamp': time.time(),
                'data': 'recovery_test_data'
            }
            await connection.send(json.dumps(recovery_message))
            recovery_response = await connection.recv()
            
            test_result.update({
                'success': True,
                'details': {
                    'initial_connection': True,
                    'initial_response': json.loads(initial_response),
                    'reconnection_successful': True,
                    'recovery_response': json.loads(recovery_response),
                    'recovery_time': time.time() - test_start
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Connection recovery test failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_voice_pipeline_end_to_end(self) -> Dict[str, Any]:
        """Test complete voice pipeline from audio input to agent response"""
        test_start = time.time()
        test_result = {
            'test_name': 'voice_pipeline_end_to_end',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        connection = None
        
        try:
            # Create synthetic audio data for testing
            sample_rate = 16000
            duration = 2.0  # 2 seconds
            frequency = 440  # A4 note
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, sample_rate)
                temp_audio_file = temp_file.name
            
            try:
                # Establish connection
                connection = await self.create_websocket_connection("voice_pipeline_test")
                
                # Send voice data message
                with open(temp_audio_file, 'rb') as f:
                    audio_bytes = f.read()
                
                voice_message = {
                    'type': 'voice_input',
                    'client_id': 'voice_pipeline_test',
                    'timestamp': time.time(),
                    'audio_format': 'wav',
                    'sample_rate': sample_rate,
                    'duration': duration,
                    'audio_data': audio_bytes.hex()  # Convert to hex string
                }
                
                await connection.send(json.dumps(voice_message))
                logger.info("Sent voice data to pipeline")
                
                # Wait for processing and response
                response = await asyncio.wait_for(connection.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                # Analyze response
                expected_fields = ['transcription', 'agent_response', 'processing_time']
                has_all_fields = all(field in response_data for field in expected_fields)
                
                test_result.update({
                    'success': has_all_fields and 'error' not in response_data,
                    'details': {
                        'audio_sent': True,
                        'response_received': True,
                        'response_complete': has_all_fields,
                        'response_data': response_data,
                        'processing_latency': response_data.get('processing_time', 'unknown')
                    }
                })
                
            finally:
                # Clean up temporary file
                os.unlink(temp_audio_file)
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Voice pipeline test failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_load_scenario(self, concurrent_clients: int = 10, duration: int = 30) -> Dict[str, Any]:
        """Test system under load with multiple concurrent clients"""
        test_start = time.time()
        test_result = {
            'test_name': 'load_scenario',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {
                'concurrent_clients': concurrent_clients,
                'test_duration': duration,
                'metrics': {}
            }
        }
        
        connections = []
        message_tasks = []
        
        try:
            # Create concurrent connections
            connection_tasks = [
                self.create_websocket_connection(f"load_client_{i}")
                for i in range(concurrent_clients)
            ]
            
            connections = await asyncio.gather(*connection_tasks)
            logger.info(f"Created {len(connections)} connections for load test")
            
            # Send messages continuously for test duration
            async def send_continuous_messages(conn, client_id):
                message_count = 0
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    try:
                        message = {
                            'type': 'voice_data',
                            'client_id': client_id,
                            'timestamp': time.time(),
                            'message_id': message_count,
                            'data': f'load_test_data_{message_count}'
                        }
                        
                        await conn.send(json.dumps(message))
                        message_count += 1
                        
                        # Small delay to simulate realistic usage
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error sending message for {client_id}: {e}")
                        break
                
                return message_count
            
            # Start continuous message sending for all clients
            message_tasks = [
                send_continuous_messages(conn, f"load_client_{i}")
                for i, conn in enumerate(connections)
            ]
            
            # Wait for all message tasks to complete
            message_counts = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            successful_counts = [
                count for count in message_counts 
                if not isinstance(count, Exception)
            ]
            
            total_messages = sum(successful_counts)
            average_messages_per_client = total_messages / len(successful_counts) if successful_counts else 0
            
            test_result.update({
                'success': len(successful_counts) >= concurrent_clients * 0.8,  # 80% success rate
                'details': {
                    'concurrent_clients': concurrent_clients,
                    'test_duration': duration,
                    'successful_clients': len(successful_counts),
                    'total_messages_sent': total_messages,
                    'average_messages_per_client': average_messages_per_client,
                    'success_rate': len(successful_counts) / concurrent_clients * 100,
                    'metrics': {
                        'messages_per_second': total_messages / duration,
                        'client_success_rate': len(successful_counts) / concurrent_clients
                    }
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Load scenario test failed: {e}")
        
        finally:
            # Close all connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run all integration tests and return comprehensive results"""
        suite_start = time.time()
        
        results = {
            'test_suite': 'mac_bridge_integration',
            'start_time': datetime.utcnow().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        # Define test sequence
        test_sequence = [
            ('single_client', self.test_single_client_connection),
            ('multiple_clients', lambda: self.test_multiple_client_connections(5)),
            ('connection_recovery', self.test_connection_recovery),
            ('voice_pipeline', self.test_voice_pipeline_end_to_end),
            ('load_scenario', lambda: self.test_load_scenario(10, 30))
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, test_func in test_sequence:
            logger.info(f"Running test: {test_name}")
            
            try:
                test_result = await test_func()
                results['tests'].append(test_result)
                
                if test_result['success']:
                    passed_tests += 1
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    failed_tests += 1
                    logger.error(f"❌ {test_name} FAILED")
                    
            except Exception as e:
                failed_tests += 1
                error_result = {
                    'test_name': test_name,
                    'success': False,
                    'error': str(e),
                    'start_time': datetime.utcnow().isoformat(),
                    'end_time': datetime.utcnow().isoformat()
                }
                results['tests'].append(error_result)
                logger.error(f"❌ {test_name} FAILED with exception: {e}")
        
        # Calculate summary
        total_tests = passed_tests + failed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        results.update({
            'end_time': datetime.utcnow().isoformat(),
            'duration': time.time() - suite_start,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': success_rate,
                'deployment_ready': success_rate >= 80
            }
        })
        
        return results

# Pytest test functions
@pytest.mark.asyncio
async def test_mac_bridge_single_connection():
    """Test single Mac client WebSocket connection"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = MacBridgeIntegrationTester(config)
    result = await tester.test_single_client_connection()
    
    assert result['success'], f"Single connection test failed: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
async def test_mac_bridge_multiple_connections():
    """Test multiple concurrent Mac client connections"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = MacBridgeIntegrationTester(config)
    result = await tester.test_multiple_client_connections(3)  # Smaller number for CI
    
    assert result['success'], f"Multiple connections test failed: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
async def test_mac_bridge_connection_recovery():
    """Test connection recovery after disconnection"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = MacBridgeIntegrationTester(config)
    result = await tester.test_connection_recovery()
    
    assert result['success'], f"Connection recovery test failed: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
@pytest.mark.slow
async def test_mac_bridge_voice_pipeline():
    """Test end-to-end voice processing pipeline"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = MacBridgeIntegrationTester(config)
    result = await tester.test_voice_pipeline_end_to_end()
    
    assert result['success'], f"Voice pipeline test failed: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
@pytest.mark.load
async def test_mac_bridge_load_scenario():
    """Test system under load with multiple clients"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = MacBridgeIntegrationTester(config)
    result = await tester.test_load_scenario(5, 10)  # Smaller load for CI
    
    assert result['success'], f"Load scenario test failed: {result.get('details', {}).get('error', 'Unknown error')}"

if __name__ == "__main__":
    # Run comprehensive test suite
    async def main():
        config = {
            'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
        }
        
        tester = MacBridgeIntegrationTester(config)
        results = await tester.run_comprehensive_test_suite()
        
        print(json.dumps(results, indent=2))
        
        if results['summary']['deployment_ready']:
            print("\n🎉 MAC BRIDGE INTEGRATION TESTS PASSED - DEPLOYMENT READY!")
            exit(0)
        else:
            print(f"\n❌ MAC BRIDGE INTEGRATION TESTS FAILED - {results['summary']['failed']} failures")
            exit(1)
    
    asyncio.run(main())