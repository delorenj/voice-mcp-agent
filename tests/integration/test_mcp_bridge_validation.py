#!/usr/bin/env python3
"""
MCP Bridge Validation Tests
Comprehensive testing for MCP server integration and tool execution validation
"""

import asyncio
import json
import logging
import pytest
import httpx
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch, AsyncMock
import yaml
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPBridgeValidator:
    """Validator for MCP server integration and tool execution"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mcp_servers = config.get('mcp_servers', [])
        self.test_results: List[Dict] = []
        self.active_clients: List[httpx.AsyncClient] = []
    
    async def create_mcp_client(self, server_config: Dict) -> httpx.AsyncClient:
        """Create MCP client for server communication"""
        try:
            headers = server_config.get('headers', {})
            timeout = httpx.Timeout(30.0)
            
            client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                verify=server_config.get('verify_ssl', True)
            )
            
            self.active_clients.append(client)
            logger.info(f"Created MCP client for {server_config.get('name', 'unknown')}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create MCP client: {e}")
            raise
    
    async def test_mcp_server_discovery(self, server_config: Dict) -> Dict[str, Any]:
        """Test MCP server discovery and tool enumeration"""
        test_start = time.time()
        test_result = {
            'test_name': 'mcp_server_discovery',
            'server_name': server_config.get('name', 'unknown'),
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        client = None
        
        try:
            client = await self.create_mcp_client(server_config)
            server_url = server_config['url']
            
            # Test server health endpoint
            health_response = await client.get(f"{server_url}/health")
            health_ok = health_response.status_code == 200
            
            # Test tool discovery endpoint
            tools_response = await client.get(f"{server_url}/tools")
            tools_ok = tools_response.status_code == 200
            
            if tools_ok:
                tools_data = tools_response.json()
                discovered_tools = tools_data.get('tools', [])
                
                test_result.update({
                    'success': health_ok and tools_ok and len(discovered_tools) > 0,
                    'details': {
                        'health_check': health_ok,
                        'tools_discovery': tools_ok,
                        'tools_count': len(discovered_tools),
                        'discovered_tools': [tool.get('name', 'unknown') for tool in discovered_tools],
                        'server_info': tools_data.get('server_info', {}),
                        'response_time': time.time() - test_start
                    }
                })
            else:
                test_result['details'] = {
                    'health_check': health_ok,
                    'tools_discovery': tools_ok,
                    'error': f"Tools discovery failed with status {tools_response.status_code}"
                }
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"MCP server discovery test failed for {server_config.get('name')}: {e}")
        
        finally:
            if client:
                await client.aclose()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_mcp_tool_execution(self, server_config: Dict, tool_name: str, 
                                    tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """Test MCP tool execution with specific parameters"""
        test_start = time.time()
        test_result = {
            'test_name': 'mcp_tool_execution',
            'server_name': server_config.get('name', 'unknown'),
            'tool_name': tool_name,
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        client = None
        
        try:
            client = await self.create_mcp_client(server_config)
            server_url = server_config['url']
            
            # Execute tool
            tool_payload = {
                'tool': tool_name,
                'parameters': tool_params
            }
            
            execution_response = await client.post(
                f"{server_url}/execute",
                json=tool_payload
            )
            
            execution_ok = execution_response.status_code == 200
            
            if execution_ok:
                execution_data = execution_response.json()
                
                # Validate response structure
                expected_fields = ['result', 'status', 'execution_time']
                has_required_fields = all(field in execution_data for field in expected_fields)
                
                test_result.update({
                    'success': execution_ok and has_required_fields,
                    'details': {
                        'execution_successful': execution_ok,
                        'response_valid': has_required_fields,
                        'execution_time': execution_data.get('execution_time', 'unknown'),
                        'result_type': type(execution_data.get('result', None)).__name__,
                        'status': execution_data.get('status', 'unknown'),
                        'response_size': len(str(execution_data)),
                        'latency': time.time() - test_start
                    }
                })
                
                # Store partial result for analysis
                if len(str(execution_data.get('result', ''))) < 1000:
                    test_result['details']['sample_result'] = execution_data.get('result')
                
            else:
                test_result['details'] = {
                    'execution_successful': execution_ok,
                    'error': f"Tool execution failed with status {execution_response.status_code}",
                    'response_text': execution_response.text[:500] if hasattr(execution_response, 'text') else ''
                }
                
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"MCP tool execution test failed for {tool_name}: {e}")
        
        finally:
            if client:
                await client.aclose()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_mcp_error_handling(self, server_config: Dict) -> Dict[str, Any]:
        """Test MCP server error handling and recovery"""
        test_start = time.time()
        test_result = {
            'test_name': 'mcp_error_handling',
            'server_name': server_config.get('name', 'unknown'),
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        client = None
        error_scenarios = []
        
        try:
            client = await self.create_mcp_client(server_config)
            server_url = server_config['url']
            
            # Test scenarios for error handling
            scenarios = [
                {
                    'name': 'invalid_tool',
                    'payload': {'tool': 'nonexistent_tool', 'parameters': {}},
                    'expected_status': [400, 404]
                },
                {
                    'name': 'invalid_parameters',
                    'payload': {'tool': 'valid_tool', 'parameters': {'invalid': 'params'}},
                    'expected_status': [400, 422]
                },
                {
                    'name': 'malformed_request',
                    'payload': {'invalid': 'structure'},
                    'expected_status': [400, 422]
                }
            ]
            
            for scenario in scenarios:
                try:
                    response = await client.post(
                        f"{server_url}/execute",
                        json=scenario['payload'],
                        timeout=10.0
                    )
                    
                    scenario_result = {
                        'scenario': scenario['name'],
                        'status_code': response.status_code,
                        'expected_error': response.status_code in scenario['expected_status'],
                        'has_error_message': 'error' in response.text.lower() or 'message' in response.text.lower()
                    }
                    
                    # Try to parse error response
                    try:
                        error_data = response.json()
                        scenario_result['error_structure_valid'] = 'error' in error_data or 'message' in error_data
                    except:
                        scenario_result['error_structure_valid'] = False
                    
                    error_scenarios.append(scenario_result)
                    
                except Exception as e:
                    error_scenarios.append({
                        'scenario': scenario['name'],
                        'exception': str(e),
                        'expected_error': False
                    })
            
            # Evaluate error handling quality
            successful_scenarios = sum(1 for s in error_scenarios if s.get('expected_error', False))
            total_scenarios = len(scenarios)
            
            test_result.update({
                'success': successful_scenarios >= total_scenarios * 0.8,  # 80% success rate
                'details': {
                    'scenarios_tested': total_scenarios,
                    'successful_error_handling': successful_scenarios,
                    'error_handling_rate': successful_scenarios / total_scenarios * 100,
                    'scenarios': error_scenarios
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"MCP error handling test failed: {e}")
        
        finally:
            if client:
                await client.aclose()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_mcp_authentication(self, server_config: Dict) -> Dict[str, Any]:
        """Test MCP server authentication mechanisms"""
        test_start = time.time()
        test_result = {
            'test_name': 'mcp_authentication',
            'server_name': server_config.get('name', 'unknown'),
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        try:
            auth_config = server_config.get('auth', {})
            
            if not auth_config:
                test_result.update({
                    'success': True,  # No auth required
                    'details': {'auth_required': False, 'auth_type': 'none'}
                })
                return test_result
            
            auth_type = auth_config.get('type', 'unknown')
            
            # Test with valid credentials
            valid_client = await self.create_mcp_client(server_config)
            
            try:
                health_response = await valid_client.get(f"{server_config['url']}/health")
                valid_auth = health_response.status_code == 200
            finally:
                await valid_client.aclose()
            
            # Test with invalid credentials
            invalid_config = server_config.copy()
            invalid_config['headers'] = {'Authorization': 'Bearer invalid_token'}
            invalid_client = await self.create_mcp_client(invalid_config)
            
            try:
                health_response = await invalid_client.get(f"{server_config['url']}/health")
                invalid_auth_rejected = health_response.status_code in [401, 403]
            finally:
                await invalid_client.aclose()
            
            test_result.update({
                'success': valid_auth and invalid_auth_rejected,
                'details': {
                    'auth_required': True,
                    'auth_type': auth_type,
                    'valid_credentials_accepted': valid_auth,
                    'invalid_credentials_rejected': invalid_auth_rejected
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"MCP authentication test failed: {e}")
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def test_mcp_concurrent_requests(self, server_config: Dict, 
                                         concurrent_count: int = 10) -> Dict[str, Any]:
        """Test MCP server handling of concurrent requests"""
        test_start = time.time()
        test_result = {
            'test_name': 'mcp_concurrent_requests',
            'server_name': server_config.get('name', 'unknown'),
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        clients = []
        
        try:
            # Create multiple clients
            clients = [
                await self.create_mcp_client(server_config)
                for _ in range(concurrent_count)
            ]
            
            server_url = server_config['url']
            
            # Define concurrent requests
            async def make_concurrent_request(client, request_id):
                try:
                    start_time = time.time()
                    
                    # Make a simple tool discovery request
                    response = await client.get(f"{server_url}/tools")
                    
                    return {
                        'request_id': request_id,
                        'success': response.status_code == 200,
                        'status_code': response.status_code,
                        'response_time': time.time() - start_time,
                        'response_size': len(response.content) if hasattr(response, 'content') else 0
                    }
                    
                except Exception as e:
                    return {
                        'request_id': request_id,
                        'success': False,
                        'error': str(e),
                        'response_time': time.time() - start_time
                    }
            
            # Execute concurrent requests
            concurrent_tasks = [
                make_concurrent_request(client, i)
                for i, client in enumerate(clients)
            ]
            
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Analyze results
            successful_requests = [
                r for r in results 
                if not isinstance(r, Exception) and r.get('success', False)
            ]
            
            failed_requests = len(results) - len(successful_requests)
            
            if successful_requests:
                avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
                max_response_time = max(r['response_time'] for r in successful_requests)
                min_response_time = min(r['response_time'] for r in successful_requests)
            else:
                avg_response_time = max_response_time = min_response_time = 0
            
            success_rate = len(successful_requests) / concurrent_count * 100
            
            test_result.update({
                'success': success_rate >= 90,  # 90% success rate required
                'details': {
                    'concurrent_requests': concurrent_count,
                    'successful_requests': len(successful_requests),
                    'failed_requests': failed_requests,
                    'success_rate': success_rate,
                    'avg_response_time': avg_response_time,
                    'max_response_time': max_response_time,
                    'min_response_time': min_response_time,
                    'performance_rating': 'good' if avg_response_time < 1.0 else 'acceptable' if avg_response_time < 3.0 else 'poor'
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"MCP concurrent requests test failed: {e}")
        
        finally:
            # Close all clients
            for client in clients:
                try:
                    await client.aclose()
                except:
                    pass
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def run_comprehensive_mcp_validation(self) -> Dict[str, Any]:
        """Run comprehensive MCP validation across all configured servers"""
        suite_start = time.time()
        
        results = {
            'validation_suite': 'mcp_bridge_validation',
            'start_time': datetime.utcnow().isoformat(),
            'servers_tested': len(self.mcp_servers),
            'server_results': [],
            'summary': {}
        }
        
        total_tests = 0
        passed_tests = 0
        
        for server_config in self.mcp_servers:
            server_name = server_config.get('name', 'unknown')
            logger.info(f"Testing MCP server: {server_name}")
            
            server_results = {
                'server_name': server_name,
                'server_url': server_config.get('url', 'unknown'),
                'tests': []
            }
            
            # Define test sequence for each server
            server_tests = [
                ('discovery', lambda: self.test_mcp_server_discovery(server_config)),
                ('authentication', lambda: self.test_mcp_authentication(server_config)),
                ('error_handling', lambda: self.test_mcp_error_handling(server_config)),
                ('concurrent_requests', lambda: self.test_mcp_concurrent_requests(server_config, 5))
            ]
            
            # Add tool execution tests if tools are specified
            if 'test_tools' in server_config:
                for tool_config in server_config['test_tools']:
                    tool_name = tool_config['name']
                    tool_params = tool_config.get('params', {})
                    server_tests.append((
                        f'tool_{tool_name}',
                        lambda tn=tool_name, tp=tool_params: self.test_mcp_tool_execution(server_config, tn, tp)
                    ))
            
            # Execute tests for this server
            server_passed = 0
            server_total = len(server_tests)
            
            for test_name, test_func in server_tests:
                try:
                    test_result = await test_func()
                    server_results['tests'].append(test_result)
                    
                    if test_result['success']:
                        server_passed += 1
                        passed_tests += 1
                        logger.info(f"✅ {server_name}.{test_name} PASSED")
                    else:
                        logger.error(f"❌ {server_name}.{test_name} FAILED")
                    
                    total_tests += 1
                    
                except Exception as e:
                    error_result = {
                        'test_name': test_name,
                        'server_name': server_name,
                        'success': False,
                        'error': str(e),
                        'start_time': datetime.utcnow().isoformat(),
                        'end_time': datetime.utcnow().isoformat()
                    }
                    server_results['tests'].append(error_result)
                    total_tests += 1
                    logger.error(f"❌ {server_name}.{test_name} FAILED with exception: {e}")
            
            # Add server summary
            server_results.update({
                'server_passed': server_passed,
                'server_total': server_total,
                'server_success_rate': (server_passed / server_total * 100) if server_total > 0 else 0
            })
            
            results['server_results'].append(server_results)
        
        # Calculate overall summary
        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        results.update({
            'end_time': datetime.utcnow().isoformat(),
            'duration': time.time() - suite_start,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': total_tests - passed_tests,
                'success_rate': overall_success_rate,
                'deployment_ready': overall_success_rate >= 85,
                'servers_healthy': sum(
                    1 for server in results['server_results']
                    if server['server_success_rate'] >= 80
                )
            }
        })
        
        return results

# Pytest test functions
@pytest.mark.asyncio
async def test_mcp_servers_discovery():
    """Test MCP server discovery for all configured servers"""
    config = load_test_config()
    validator = MCPBridgeValidator(config)
    
    for server_config in config.get('mcp_servers', []):
        result = await validator.test_mcp_server_discovery(server_config)
        assert result['success'], f"Discovery failed for {server_config.get('name')}: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio 
async def test_mcp_servers_authentication():
    """Test MCP server authentication mechanisms"""
    config = load_test_config()
    validator = MCPBridgeValidator(config)
    
    for server_config in config.get('mcp_servers', []):
        result = await validator.test_mcp_authentication(server_config)
        assert result['success'], f"Authentication test failed for {server_config.get('name')}: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
async def test_mcp_servers_error_handling():
    """Test MCP server error handling capabilities"""
    config = load_test_config()
    validator = MCPBridgeValidator(config)
    
    for server_config in config.get('mcp_servers', []):
        result = await validator.test_mcp_error_handling(server_config)
        assert result['success'], f"Error handling test failed for {server_config.get('name')}: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
@pytest.mark.load
async def test_mcp_servers_concurrent_load():
    """Test MCP servers under concurrent load"""
    config = load_test_config()
    validator = MCPBridgeValidator(config)
    
    for server_config in config.get('mcp_servers', []):
        result = await validator.test_mcp_concurrent_requests(server_config, 5)
        assert result['success'], f"Concurrent load test failed for {server_config.get('name')}: {result.get('details', {}).get('error', 'Unknown error')}"

def load_test_config() -> Dict[str, Any]:
    """Load test configuration from environment and files"""
    config = {
        'mcp_servers': []
    }
    
    # Try to load from mcp_servers.yaml
    config_file = os.getenv('MCP_CONFIG_FILE', 'mcp_servers.yaml')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            file_config = yaml.safe_load(f)
            config['mcp_servers'] = file_config.get('servers', [])
    
    # Override with test-specific configurations
    test_config_file = os.getenv('TEST_MCP_CONFIG_FILE', 'test_mcp_config.yaml')
    if os.path.exists(test_config_file):
        with open(test_config_file, 'r') as f:
            test_config = yaml.safe_load(f)
            config.update(test_config)
    
    return config

if __name__ == "__main__":
    # Run comprehensive MCP validation
    async def main():
        config = load_test_config()
        validator = MCPBridgeValidator(config)
        results = await validator.run_comprehensive_mcp_validation()
        
        print(json.dumps(results, indent=2))
        
        if results['summary']['deployment_ready']:
            print(f"\n🎉 MCP BRIDGE VALIDATION PASSED - {results['summary']['servers_healthy']}/{len(config['mcp_servers'])} servers healthy")
            exit(0)
        else:
            print(f"\n❌ MCP BRIDGE VALIDATION FAILED - {results['summary']['failed']} test failures")
            exit(1)
    
    asyncio.run(main())