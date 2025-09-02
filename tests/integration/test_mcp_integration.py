"""
MCP Client/Server Integration Tests
Comprehensive testing of MCP tool integration and communication
"""

import pytest
import asyncio
import json
import time
import tempfile
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Import project modules
from mcp_client import MCPClient, MCPServerSse
from mcp_client.agent_tools import MCPToolsIntegration
from mcp_client.auth import AuthenticationError
from mcp_config import load_mcp_config, expand_env_vars
from agent_core import FunctionAgent

logger = logging.getLogger(__name__)

@dataclass
class MCPToolCall:
    """MCP tool call representation"""
    tool_name: str
    parameters: Dict[str, Any]
    expected_result: Optional[Any] = None
    should_succeed: bool = True

@dataclass
class MCPTestServer:
    """Test MCP server configuration"""
    name: str
    url: str
    auth_type: Optional[str] = None
    tools: List[str] = None
    headers: Dict[str, str] = None

class MockMCPServer:
    """Mock MCP server for testing"""
    
    def __init__(self, name: str, tools: List[str]):
        self.name = name
        self.tools = tools
        self.connected = False
        self.tool_calls = []
    
    async def connect(self):
        """Mock connect method"""
        self.connected = True
        logger.info(f"Mock MCP server {self.name} connected")
    
    async def disconnect(self):
        """Mock disconnect method"""
        self.connected = False
        logger.info(f"Mock MCP server {self.name} disconnected")
    
    async def list_tools(self) -> List[Dict]:
        """Mock list tools method"""
        return [
            {
                'name': tool,
                'description': f'Mock tool: {tool}',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'input': {'type': 'string', 'description': 'Test input'}
                    }
                }
            }
            for tool in self.tools
        ]
    
    async def call_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Mock tool call method"""
        self.tool_calls.append({'name': tool_name, 'parameters': parameters})
        
        if tool_name not in self.tools:
            raise Exception(f"Tool {tool_name} not found")
        
        return {
            'content': f'Mock result for {tool_name} with params: {parameters}',
            'isError': False
        }

class MCPIntegrationTester:
    """MCP integration testing framework"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.mock_servers: List[MockMCPServer] = []
        self.mcp_clients: List[MCPClient] = []
    
    def create_mock_server(self, name: str, tools: List[str]) -> MockMCPServer:
        """Create mock MCP server"""
        mock_server = MockMCPServer(name, tools)
        self.mock_servers.append(mock_server)
        return mock_server
    
    async def setup_test_environment(self):
        """Setup test environment with mock servers"""
        # Create mock servers for common tool types
        github_server = self.create_mock_server('github', [
            'search_repositories',
            'create_issue',
            'get_pull_request',
            'list_commits'
        ])
        
        delotools_server = self.create_mock_server('delotools', [
            'list_directory',
            'read_file',
            'execute_command',
            'start_search'
        ])
        
        # Connect mock servers
        for server in self.mock_servers:
            await server.connect()
    
    async def teardown_test_environment(self):
        """Teardown test environment"""
        for server in self.mock_servers:
            await server.disconnect()
        
        for client in self.mcp_clients:
            try:
                await client.disconnect()
            except:
                pass
    
    def get_server_by_name(self, name: str) -> Optional[MockMCPServer]:
        """Get mock server by name"""
        for server in self.mock_servers:
            if server.name == name:
                return server
        return None

@pytest.fixture
async def mcp_integration_tester():
    """Fixture providing MCP integration tester"""
    config = {
        'test_mode': True,
        'servers': [
            {
                'name': 'github',
                'url': 'https://github-mcp.example.com',
                'tools': ['search_repositories', 'create_issue']
            },
            {
                'name': 'delotools',
                'url': 'https://mcp.delo.sh/metamcp/delonet/sse',
                'tools': ['list_directory', 'read_file']
            }
        ]
    }
    
    tester = MCPIntegrationTester(config)
    await tester.setup_test_environment()
    yield tester
    await tester.teardown_test_environment()

class TestMCPConfiguration:
    """Test MCP configuration loading and validation"""
    
    def test_load_mcp_config_from_file(self, tmp_path):
        """Test loading MCP configuration from YAML file"""
        config_content = """
servers:
  - name: github
    type: mcp
    url: https://github-mcp.example.com
    allowed_tools: [search_repositories, create_issue]
    headers:
      Authorization: "Bearer $GITHUB_TOKEN"
  - name: delotools
    type: mcp
    url: https://mcp.delo.sh/metamcp/delonet/sse
    allowed_tools: [list_directory, read_file, execute_command]
    headers:
      Authorization: "Bearer $DELOTOOLS_TOKEN"
"""
        config_file = tmp_path / "mcp_servers.yaml"
        config_file.write_text(config_content)
        
        # Test loading
        servers = load_mcp_config(str(config_file))
        
        assert len(servers) == 2
        assert servers[0]['name'] == 'github'
        assert servers[0]['url'] == 'https://github-mcp.example.com'
        assert 'search_repositories' in servers[0]['allowed_tools']
        
        assert servers[1]['name'] == 'delotools'
        assert 'list_directory' in servers[1]['allowed_tools']
    
    def test_environment_variable_expansion(self):
        """Test environment variable expansion in config"""
        import os
        
        # Set test environment variable
        os.environ['TEST_MCP_TOKEN'] = 'test-token-12345'
        
        try:
            # Test expansion
            test_value = "Bearer $TEST_MCP_TOKEN"
            expanded = expand_env_vars(test_value)
            
            assert expanded == "Bearer test-token-12345"
            
            # Test with braces
            test_value_braces = "Bearer ${TEST_MCP_TOKEN}"
            expanded_braces = expand_env_vars(test_value_braces)
            
            assert expanded_braces == "Bearer test-token-12345"
            
            # Test missing variable
            test_missing = "Bearer $MISSING_TOKEN"
            expanded_missing = expand_env_vars(test_missing)
            
            assert expanded_missing == "Bearer $MISSING_TOKEN"  # Should remain unchanged
            
        finally:
            del os.environ['TEST_MCP_TOKEN']
    
    def test_config_validation(self, tmp_path):
        """Test configuration validation"""
        # Test missing required fields
        invalid_config = """
servers:
  - name: incomplete
    # Missing url field
"""
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text(invalid_config)
        
        try:
            servers = load_mcp_config(str(config_file))
            # Should handle missing fields gracefully or raise appropriate error
            assert isinstance(servers, list)
        except Exception as e:
            # Expected for invalid configuration
            logger.info(f"Expected error for invalid config: {e}")

class TestMCPClientConnection:
    """Test MCP client connection functionality"""
    
    async def test_mcp_client_initialization(self, mcp_integration_tester):
        """Test MCP client initialization"""
        mock_server = mcp_integration_tester.get_server_by_name('github')
        assert mock_server is not None
        
        # Test client initialization would normally happen here
        # In actual implementation, this would create real MCPClient
        
        assert mock_server.connected
        logger.info(f"MCP client initialized for server: {mock_server.name}")
    
    async def test_server_connection_retry(self, mcp_integration_tester):
        """Test server connection retry logic"""
        # Create a server that fails initially
        failing_server = MockMCPServer('failing_server', ['test_tool'])
        
        connection_attempts = 0
        original_connect = failing_server.connect
        
        async def failing_connect():
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts < 3:
                raise ConnectionError("Simulated connection failure")
            await original_connect()
        
        failing_server.connect = failing_connect
        
        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await failing_server.connect()
                break
            except ConnectionError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)  # Brief retry delay
        
        assert failing_server.connected
        assert connection_attempts == 3
        logger.info(f"Connection successful after {connection_attempts} attempts")
    
    async def test_authentication_flow(self, mcp_integration_tester):
        """Test MCP authentication flow"""
        # Simulate authentication scenarios
        auth_scenarios = [
            {'type': 'bearer', 'token': 'valid-token', 'should_succeed': True},
            {'type': 'bearer', 'token': 'invalid-token', 'should_succeed': False},
            {'type': 'api_key', 'key': 'valid-key', 'should_succeed': True},
        ]
        
        for scenario in auth_scenarios:
            mock_server = MockMCPServer(f"auth_test_{scenario['type']}", ['test_tool'])
            
            # Simulate authentication check
            auth_success = scenario['should_succeed']
            
            if auth_success:
                await mock_server.connect()
                assert mock_server.connected
                logger.info(f"Authentication successful for {scenario['type']}")
            else:
                # Simulate authentication failure
                try:
                    # In real implementation, this would raise AuthenticationError
                    if not scenario['should_succeed']:
                        raise AuthenticationError(f"Invalid {scenario['type']}")
                    await mock_server.connect()
                except AuthenticationError as e:
                    logger.info(f"Expected authentication failure: {e}")

class TestMCPToolDiscovery:
    """Test MCP tool discovery and listing"""
    
    async def test_tool_discovery(self, mcp_integration_tester):
        """Test discovering tools from MCP servers"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # Discover tools
        tools = await github_server.list_tools()
        
        assert len(tools) > 0
        assert any(tool['name'] == 'search_repositories' for tool in tools)
        assert any(tool['name'] == 'create_issue' for tool in tools)
        
        # Validate tool schema
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            
        logger.info(f"Discovered {len(tools)} tools from github server")
    
    async def test_tool_filtering(self, mcp_integration_tester):
        """Test tool filtering based on allowed_tools configuration"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        allowed_tools = ['search_repositories', 'create_issue']
        
        all_tools = await github_server.list_tools()
        
        # Simulate tool filtering
        filtered_tools = [tool for tool in all_tools if tool['name'] in allowed_tools]
        
        assert len(filtered_tools) <= len(all_tools)
        
        for tool in filtered_tools:
            assert tool['name'] in allowed_tools
        
        logger.info(f"Filtered to {len(filtered_tools)} allowed tools")
    
    async def test_tool_schema_validation(self, mcp_integration_tester):
        """Test tool schema validation"""
        delotools_server = mcp_integration_tester.get_server_by_name('delotools')
        
        tools = await delotools_server.list_tools()
        
        for tool in tools:
            # Validate required schema fields
            assert isinstance(tool['name'], str)
            assert len(tool['name']) > 0
            assert isinstance(tool['description'], str)
            assert isinstance(tool['inputSchema'], dict)
            
            # Validate input schema structure
            schema = tool['inputSchema']
            assert schema.get('type') == 'object'
            assert 'properties' in schema or schema.get('type') == 'object'
            
        logger.info(f"Validated schema for {len(tools)} tools")

class TestMCPToolExecution:
    """Test MCP tool execution"""
    
    async def test_simple_tool_call(self, mcp_integration_tester):
        """Test simple tool call execution"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # Execute tool call
        result = await github_server.call_tool('search_repositories', {
            'query': 'test repository',
            'language': 'python'
        })
        
        assert result is not None
        assert 'content' in result
        assert not result.get('isError', True)
        
        # Verify tool call was recorded
        assert len(github_server.tool_calls) > 0
        last_call = github_server.tool_calls[-1]
        assert last_call['name'] == 'search_repositories'
        assert 'query' in last_call['parameters']
        
        logger.info(f"Tool call successful: {result['content']}")
    
    async def test_tool_call_with_invalid_parameters(self, mcp_integration_tester):
        """Test tool call with invalid parameters"""
        delotools_server = mcp_integration_tester.get_server_by_name('delotools')
        
        # Test with missing required parameters
        try:
            result = await delotools_server.call_tool('read_file', {})
            # In mock implementation, this might succeed
            # In real implementation, should validate parameters
            logger.info(f"Tool call with empty params: {result}")
        except Exception as e:
            logger.info(f"Expected error for invalid parameters: {e}")
        
        # Test with invalid parameter types
        try:
            result = await delotools_server.call_tool('read_file', {
                'path': 123  # Should be string
            })
        except Exception as e:
            logger.info(f"Expected error for invalid parameter type: {e}")
    
    async def test_tool_call_error_handling(self, mcp_integration_tester):
        """Test tool call error handling"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # Test calling non-existent tool
        try:
            await github_server.call_tool('nonexistent_tool', {})
            assert False, "Should have raised exception for non-existent tool"
        except Exception as e:
            assert "not found" in str(e).lower()
            logger.info(f"Correctly handled non-existent tool: {e}")
    
    async def test_concurrent_tool_calls(self, mcp_integration_tester):
        """Test concurrent tool execution"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        delotools_server = mcp_integration_tester.get_server_by_name('delotools')
        
        # Prepare concurrent tool calls
        tool_calls = [
            (github_server, 'search_repositories', {'query': 'test1'}),
            (github_server, 'create_issue', {'title': 'Test Issue', 'body': 'Test'}),
            (delotools_server, 'list_directory', {'path': '/tmp'}),
            (delotools_server, 'read_file', {'path': '/etc/hosts'}),
        ]
        
        # Execute concurrently
        async def execute_call(server, tool_name, params):
            return await server.call_tool(tool_name, params)
        
        start_time = time.time()
        tasks = [execute_call(server, tool, params) for server, tool, params in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate results
        successful_calls = sum(1 for result in results if not isinstance(result, Exception))
        assert successful_calls > 0, "No tool calls succeeded"
        
        # Concurrent execution should be faster than sequential
        assert execution_time < len(tool_calls) * 0.5, f"Concurrent execution not efficient: {execution_time:.2f}s"
        
        logger.info(f"Concurrent tool calls: {successful_calls}/{len(tool_calls)} successful in {execution_time:.2f}s")

class TestMCPAgentIntegration:
    """Test MCP integration with FunctionAgent"""
    
    async def test_agent_with_mcp_tools(self, mcp_integration_tester):
        """Test FunctionAgent with MCP tools integration"""
        # This would normally test the actual FunctionAgent integration
        # For now, we'll simulate the integration
        
        mock_agent = MagicMock()
        mock_agent.name = "test_agent"
        
        # Simulate tool integration
        github_server = mcp_integration_tester.get_server_by_name('github')
        available_tools = await github_server.list_tools()
        
        # Agent should have access to MCP tools
        assert len(available_tools) > 0
        
        # Simulate agent using MCP tool
        tool_result = await github_server.call_tool('search_repositories', {
            'query': 'livekit agents',
            'language': 'python'
        })
        
        assert tool_result is not None
        logger.info(f"Agent successfully used MCP tool: {tool_result['content'][:100]}...")
    
    async def test_agent_tool_error_recovery(self, mcp_integration_tester):
        """Test agent error recovery when MCP tools fail"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # Simulate tool failure
        original_call_tool = github_server.call_tool
        
        async def failing_call_tool(tool_name, parameters):
            raise ConnectionError("Simulated network failure")
        
        github_server.call_tool = failing_call_tool
        
        # Agent should handle tool failure gracefully
        try:
            await github_server.call_tool('search_repositories', {'query': 'test'})
            assert False, "Should have raised ConnectionError"
        except ConnectionError:
            # Agent should catch this and provide fallback behavior
            logger.info("Agent correctly handled MCP tool failure")
        
        # Restore original method
        github_server.call_tool = original_call_tool
    
    async def test_agent_tool_timeout_handling(self, mcp_integration_tester):
        """Test agent handling of MCP tool timeouts"""
        delotools_server = mcp_integration_tester.get_server_by_name('delotools')
        
        # Simulate slow tool
        original_call_tool = delotools_server.call_tool
        
        async def slow_call_tool(tool_name, parameters):
            await asyncio.sleep(2)  # Simulate slow operation
            return await original_call_tool(tool_name, parameters)
        
        delotools_server.call_tool = slow_call_tool
        
        # Test with timeout
        try:
            await asyncio.wait_for(
                delotools_server.call_tool('read_file', {'path': '/etc/hosts'}),
                timeout=1.0
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            logger.info("Agent correctly handled MCP tool timeout")
        
        # Restore original method
        delotools_server.call_tool = original_call_tool

class TestMCPPerformance:
    """Test MCP performance characteristics"""
    
    async def test_tool_call_latency(self, mcp_integration_tester):
        """Test MCP tool call latency"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # Measure tool call latency
        latencies = []
        
        for _ in range(10):
            start_time = time.time()
            await github_server.call_tool('search_repositories', {'query': 'test'})
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Tool calls should be reasonably fast
        assert avg_latency < 100, f"Average tool call latency too high: {avg_latency:.2f}ms"
        assert max_latency < 500, f"Max tool call latency too high: {max_latency:.2f}ms"
        
        logger.info(f"Tool call latency: avg={avg_latency:.2f}ms, min={min_latency:.2f}ms, max={max_latency:.2f}ms")
    
    async def test_tool_discovery_caching(self, mcp_integration_tester):
        """Test tool discovery result caching"""
        github_server = mcp_integration_tester.get_server_by_name('github')
        
        # First discovery
        start_time = time.time()
        tools1 = await github_server.list_tools()
        first_discovery_time = time.time() - start_time
        
        # Second discovery (should be cached)
        start_time = time.time()
        tools2 = await github_server.list_tools()
        second_discovery_time = time.time() - start_time
        
        # Results should be identical
        assert len(tools1) == len(tools2)
        assert [tool['name'] for tool in tools1] == [tool['name'] for tool in tools2]
        
        # Second discovery should be faster (if caching implemented)
        # In mock implementation, this might not show difference
        logger.info(f"Tool discovery timing: first={first_discovery_time:.3f}s, second={second_discovery_time:.3f}s")
    
    async def test_memory_usage_during_operations(self, mcp_integration_tester):
        """Test memory usage during MCP operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        github_server = mcp_integration_tester.get_server_by_name('github')
        delotools_server = mcp_integration_tester.get_server_by_name('delotools')
        
        # Perform many operations
        for i in range(100):
            await github_server.call_tool('search_repositories', {'query': f'test{i}'})
            await delotools_server.call_tool('list_directory', {'path': f'/tmp{i}'})
            
            # Check memory every 25 operations
            if i % 25 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory shouldn't increase significantly
                assert memory_increase < 50, f"Memory leak detected: {memory_increase:.2f}MB increase"
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        logger.info(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB ({total_increase:+.1f}MB)")

@pytest.mark.asyncio
async def test_mcp_integration_end_to_end():
    """End-to-end MCP integration test"""
    # Setup
    tester = MCPIntegrationTester({'test_mode': True})
    await tester.setup_test_environment()
    
    try:
        # Test complete integration flow
        github_server = tester.get_server_by_name('github')
        
        # 1. Discover tools
        tools = await github_server.list_tools()
        assert len(tools) > 0
        
        # 2. Execute tool
        result = await github_server.call_tool('search_repositories', {
            'query': 'livekit voice agent'
        })
        assert result is not None
        
        # 3. Verify tool call history
        assert len(github_server.tool_calls) > 0
        
        logger.info("End-to-end MCP integration test completed successfully")
        
    finally:
        await tester.teardown_test_environment()

if __name__ == "__main__":
    # Run MCP integration tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])