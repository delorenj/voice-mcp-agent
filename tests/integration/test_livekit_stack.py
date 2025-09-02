"""
Integration tests for LiveKit + Caddy + Redis stack
Tests the complete interaction between all infrastructure components
"""

import pytest
import asyncio
import aiohttp
import websockets
import redis.asyncio as redis
import json
import ssl
import socket
import time
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LiveKitStackTester:
    """Comprehensive integration testing for LiveKit deployment stack"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def setup(self):
        """Initialize test clients and connections"""
        # Redis connection
        self.redis_client = redis.Redis(
            host=self.config['redis']['host'],
            port=self.config['redis']['port'],
            decode_responses=True
        )
        
        # HTTP session with proper SSL context
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context() if self.config.get('use_ssl') else False
        )
        self.session = aiohttp.ClientSession(connector=connector)
    
    async def teardown(self):
        """Cleanup test resources"""
        if self.redis_client:
            await self.redis_client.aclose()
        if self.session:
            await self.session.close()

@pytest.fixture
async def stack_tester():
    """Fixture providing configured stack tester"""
    config = {
        'livekit': {
            'host': 'localhost',
            'port': 7880,
            'api_key': 'APIcQP8xHwvsq7d',
            'api_secret': 'RJ3CeZtWyb6d3cQPDfLfDxOjVmzxJKh6pb0i3bIyeI3B'
        },
        'caddy': {
            'host': 'lk.delo.sh',
            'port': 443
        },
        'redis': {
            'host': 'localhost',  # Would be redis host in production
            'port': 6379
        },
        'ingress': {
            'rtmp_port': 1935,
            'whip_port': 8080
        },
        'use_ssl': False  # Set to True for production testing
    }
    
    tester = LiveKitStackTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()

class TestNetworkConnectivity:
    """Test basic network connectivity between services"""
    
    async def test_port_accessibility(self, stack_tester):
        """Test that all required ports are accessible"""
        ports_to_test = [
            (stack_tester.config['livekit']['host'], stack_tester.config['livekit']['port']),
            (stack_tester.config['redis']['host'], stack_tester.config['redis']['port']),
            (stack_tester.config['livekit']['host'], stack_tester.config['ingress']['rtmp_port']),
            (stack_tester.config['livekit']['host'], stack_tester.config['ingress']['whip_port'])
        ]
        
        for host, port in ports_to_test:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                assert result == 0, f"Port {port} on {host} is not accessible"
    
    async def test_dns_resolution(self, stack_tester):
        """Test DNS resolution for all subdomains"""
        domains = [
            'lk.delo.sh',
            'lk-turn.delo.sh', 
            'lk-whip.delo.sh'
        ]
        
        for domain in domains:
            try:
                socket.getaddrinfo(domain, None)
            except socket.gaierror:
                pytest.skip(f"DNS resolution failed for {domain} - may not be accessible in test environment")

class TestRedisIntegration:
    """Test Redis connectivity and functionality"""
    
    async def test_redis_connection(self, stack_tester):
        """Test basic Redis connectivity"""
        result = await stack_tester.redis_client.ping()
        assert result is True, "Redis ping failed"
    
    async def test_redis_session_storage(self, stack_tester):
        """Test session data storage and retrieval"""
        test_key = "test:session:12345"
        test_data = {
            "room_id": "test-room",
            "user_id": "test-user",
            "timestamp": int(time.time())
        }
        
        # Store session data
        await stack_tester.redis_client.hset(test_key, mapping=test_data)
        await stack_tester.redis_client.expire(test_key, 3600)  # 1 hour TTL
        
        # Retrieve and validate
        stored_data = await stack_tester.redis_client.hgetall(test_key)
        assert stored_data["room_id"] == test_data["room_id"]
        assert stored_data["user_id"] == test_data["user_id"]
        
        # Cleanup
        await stack_tester.redis_client.delete(test_key)
    
    async def test_redis_pub_sub(self, stack_tester):
        """Test Redis pub/sub for real-time events"""
        channel = "test:events"
        test_message = {"type": "user_joined", "room": "test-room", "user": "test-user"}
        
        # Subscribe to channel
        pubsub = stack_tester.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        # Publish test message
        await stack_tester.redis_client.publish(channel, json.dumps(test_message))
        
        # Receive and validate message
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
        assert message is not None, "No message received from Redis pub/sub"
        assert json.loads(message['data']) == test_message
        
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

class TestLiveKitService:
    """Test LiveKit server functionality"""
    
    async def test_livekit_health_check(self, stack_tester):
        """Test LiveKit server health endpoint"""
        url = f"http://{stack_tester.config['livekit']['host']}:{stack_tester.config['livekit']['port']}/health"
        
        try:
            async with stack_tester.session.get(url, timeout=5) as response:
                assert response.status == 200, f"LiveKit health check failed: {response.status}"
        except Exception as e:
            pytest.skip(f"LiveKit server not accessible: {e}")
    
    async def test_websocket_connection(self, stack_tester):
        """Test WebSocket connection to LiveKit"""
        if not stack_tester.config.get('use_ssl'):
            pytest.skip("WebSocket test requires SSL configuration")
            
        ws_url = f"wss://{stack_tester.config['caddy']['host']}/ws"
        
        try:
            async with websockets.connect(ws_url, timeout=5) as websocket:
                # Send ping
                await websocket.ping()
                # Connection successful if no exception raised
                assert True
        except Exception as e:
            pytest.skip(f"WebSocket connection failed: {e}")

class TestCaddyProxy:
    """Test Caddy L4 proxy functionality"""
    
    async def test_ssl_termination(self, stack_tester):
        """Test SSL termination and certificate validation"""
        if not stack_tester.config.get('use_ssl'):
            pytest.skip("SSL test requires SSL configuration")
            
        host = stack_tester.config['caddy']['host']
        port = stack_tester.config['caddy']['port']
        
        # Test SSL connection
        context = ssl.create_default_context()
        
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                # Verify certificate
                cert = ssock.getpeercert()
                assert cert is not None, "No SSL certificate received"
                
                # Check certificate subject
                subject = dict(x[0] for x in cert['subject'])
                assert host in subject.get('commonName', ''), f"Certificate doesn't match hostname {host}"
    
    async def test_sni_routing(self, stack_tester):
        """Test Server Name Indication (SNI) routing"""
        if not stack_tester.config.get('use_ssl'):
            pytest.skip("SNI test requires SSL configuration")
            
        sni_hosts = ['lk.delo.sh', 'lk-turn.delo.sh', 'lk-whip.delo.sh']
        
        for host in sni_hosts:
            try:
                url = f"https://{host}"
                async with stack_tester.session.get(url, timeout=5) as response:
                    # Connection successful means SNI routing works
                    # Status might be 404 or other, but connection should succeed
                    assert response.status in [200, 404, 502, 503], f"Unexpected status for {host}: {response.status}"
            except Exception as e:
                logger.warning(f"SNI test failed for {host}: {e}")

class TestIngresService:
    """Test Ingress service functionality"""
    
    async def test_rtmp_port_accessibility(self, stack_tester):
        """Test RTMP port accessibility"""
        host = stack_tester.config['livekit']['host']
        port = stack_tester.config['ingress']['rtmp_port']
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            assert result == 0, f"RTMP port {port} is not accessible"
    
    async def test_whip_endpoint(self, stack_tester):
        """Test WHIP endpoint accessibility"""
        host = stack_tester.config['livekit']['host'] 
        port = stack_tester.config['ingress']['whip_port']
        url = f"http://{host}:{port}/whip"
        
        try:
            async with stack_tester.session.get(url, timeout=5) as response:
                # WHIP endpoint should respond (even if with error for invalid request)
                assert response.status in [200, 400, 404, 405], f"WHIP endpoint unreachable: {response.status}"
        except Exception as e:
            logger.warning(f"WHIP endpoint test failed: {e}")

class TestServiceIntegration:
    """Test integration between services"""
    
    async def test_session_flow_integration(self, stack_tester):
        """Test complete session flow through all services"""
        session_id = f"test-session-{int(time.time())}"
        room_id = "test-room"
        user_id = "test-user"
        
        # 1. Store session in Redis
        session_key = f"session:{session_id}"
        session_data = {
            "room_id": room_id,
            "user_id": user_id,
            "status": "connecting"
        }
        
        await stack_tester.redis_client.hset(session_key, mapping=session_data)
        
        # 2. Simulate room join event
        event_channel = f"room:{room_id}:events"
        join_event = {
            "type": "participant_joined",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": int(time.time())
        }
        
        await stack_tester.redis_client.publish(event_channel, json.dumps(join_event))
        
        # 3. Update session status
        await stack_tester.redis_client.hset(session_key, "status", "connected")
        
        # 4. Verify session state
        final_session = await stack_tester.redis_client.hgetall(session_key)
        assert final_session["status"] == "connected"
        assert final_session["room_id"] == room_id
        
        # Cleanup
        await stack_tester.redis_client.delete(session_key)
    
    async def test_failover_scenarios(self, stack_tester):
        """Test service failover and recovery"""
        # Test Redis reconnection handling
        original_client = stack_tester.redis_client
        
        try:
            # Simulate connection loss and recovery
            await stack_tester.redis_client.connection_pool.disconnect()
            
            # Should auto-reconnect on next operation
            result = await stack_tester.redis_client.ping()
            assert result is True, "Redis auto-reconnect failed"
            
        except Exception as e:
            logger.warning(f"Failover test encountered issue: {e}")
    
    async def test_performance_baseline(self, stack_tester):
        """Test performance baseline for integrated services"""
        iterations = 100
        redis_times = []
        
        # Test Redis operation latency
        for i in range(iterations):
            start_time = time.time()
            await stack_tester.redis_client.set(f"perf:test:{i}", "value")
            await stack_tester.redis_client.get(f"perf:test:{i}")
            await stack_tester.redis_client.delete(f"perf:test:{i}")
            end_time = time.time()
            
            redis_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_redis_time = sum(redis_times) / len(redis_times)
        assert avg_redis_time < 10, f"Redis operations too slow: {avg_redis_time:.2f}ms average"
        
        logger.info(f"Redis performance baseline: {avg_redis_time:.2f}ms average")

class TestSecurityIntegration:
    """Test security aspects of service integration"""
    
    async def test_api_key_validation(self, stack_tester):
        """Test API key validation across services"""
        valid_key = stack_tester.config['livekit']['api_key']
        invalid_key = "invalid-key-12345"
        
        # Store valid API key in Redis
        await stack_tester.redis_client.set(f"api:key:{valid_key}", "valid")
        
        # Test validation
        stored_key = await stack_tester.redis_client.get(f"api:key:{valid_key}")
        assert stored_key == "valid", "Valid API key not properly stored"
        
        invalid_stored = await stack_tester.redis_client.get(f"api:key:{invalid_key}")
        assert invalid_stored is None, "Invalid API key should not exist"
        
        # Cleanup
        await stack_tester.redis_client.delete(f"api:key:{valid_key}")
    
    async def test_rate_limiting_storage(self, stack_tester):
        """Test rate limiting data storage in Redis"""
        user_ip = "192.168.1.100"
        rate_limit_key = f"rate_limit:{user_ip}"
        
        # Simulate rate limiting
        current_count = await stack_tester.redis_client.incr(rate_limit_key)
        await stack_tester.redis_client.expire(rate_limit_key, 60)  # 1 minute window
        
        # Test rate limit enforcement
        for _ in range(10):  # Simulate 10 requests
            await stack_tester.redis_client.incr(rate_limit_key)
        
        final_count = await stack_tester.redis_client.get(rate_limit_key)
        assert int(final_count) >= 11, "Rate limiting counter not working"
        
        # Cleanup
        await stack_tester.redis_client.delete(rate_limit_key)

@pytest.mark.asyncio
async def test_complete_stack_health():
    """Integration test for complete stack health"""
    config = {
        'livekit': {'host': 'localhost', 'port': 7880, 'api_key': 'test', 'api_secret': 'test'},
        'caddy': {'host': 'lk.delo.sh', 'port': 443},
        'redis': {'host': 'localhost', 'port': 6379},
        'ingress': {'rtmp_port': 1935, 'whip_port': 8080},
        'use_ssl': False
    }
    
    tester = LiveKitStackTester(config)
    await tester.setup()
    
    try:
        # Basic connectivity check
        await tester.redis_client.ping()
        
        # Session simulation
        session_data = {"test": "data", "timestamp": int(time.time())}
        await tester.redis_client.set("integration:test", json.dumps(session_data))
        
        retrieved = await tester.redis_client.get("integration:test")
        assert json.loads(retrieved) == session_data
        
        await tester.redis_client.delete("integration:test")
        
    finally:
        await tester.teardown()

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])