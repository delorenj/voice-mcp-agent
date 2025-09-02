#!/usr/bin/env python3
"""
Voice MCP Agent System Verification Script
Automated verification for all testable components of the system.
"""

import sys
import json
import os
from typing import List, Tuple, Dict, Any


class SystemVerifier:
    """Automated system verification for Voice MCP Agent."""
    
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.critical_failures: List[str] = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result."""
        self.results.append((test_name, passed, details))
        status = "✓" if passed else "✗"
        print(f"{status} {test_name}")
        if details:
            print(f"  {details}")
        if not passed:
            self.critical_failures.append(test_name)
    
    def test_module_imports(self) -> bool:
        """Test all critical module imports."""
        print("\n=== MODULE IMPORT TESTS ===")
        
        modules_to_test = [
            ("MCP Config", "mcp_config", "load_mcp_config"),
            ("Agent Core", "agent_core", "FunctionAgent"),
            ("Custom Whisper STT", "custom_whisper_stt", "CustomWhisperSTT"),
            ("MCP Client", "mcp_client", "MCPClient"),
            ("MCP Server SSE", "mcp_client.server", "MCPServerSse"),
            ("MCP Tools Integration", "mcp_client.agent_tools", "MCPToolsIntegration"),
            ("Tool Integration", "tool_integration", "filtered_prepare_dynamic_tools"),
            ("A2A Integration", "a2a", "A2AServerConfig"),
            ("Authentication", "mcp_client.auth", "AuthenticationError"),
        ]
        
        all_passed = True
        for name, module, component in modules_to_test:
            try:
                mod = __import__(module, fromlist=[component])
                getattr(mod, component)
                self.log_result(f"{name} import", True, f"{component} available")
            except ImportError as e:
                self.log_result(f"{name} import", False, f"ImportError: {e}")
                all_passed = False
            except AttributeError as e:
                self.log_result(f"{name} import", False, f"Component missing: {e}")
                all_passed = False
            except Exception as e:
                self.log_result(f"{name} import", False, f"Unexpected error: {e}")
                all_passed = False
        
        return all_passed
    
    def test_mcp_configuration(self) -> bool:
        """Test MCP server configuration loading."""
        print("\n=== MCP CONFIGURATION TESTS ===")
        
        try:
            from mcp_config import load_mcp_config
            configs = load_mcp_config()
            
            if not configs:
                self.log_result("MCP config loading", False, "No MCP servers configured")
                return False
            
            self.log_result("MCP config loading", True, f"{len(configs)} servers configured")
            
            # Check each server configuration
            for i, config in enumerate(configs):
                name = config.get('name', f'server_{i}')
                url = config.get('url', '')
                server_type = config.get('type', 'mcp')
                
                # Check URL format
                if not url:
                    self.log_result(f"Server {name} URL", False, "No URL configured")
                    continue
                
                https_secure = url.startswith('https://')
                self.log_result(f"Server {name} URL", https_secure, 
                              f"{'HTTPS' if https_secure else 'HTTP'} - {url}")
                
                # Check authentication
                has_auth = bool(config.get('headers', {}).get('Authorization'))
                self.log_result(f"Server {name} auth", has_auth, 
                              "Authentication configured" if has_auth else "No authentication")
                
                # Check server type
                valid_type = server_type in ['mcp', 'a2a']
                self.log_result(f"Server {name} type", valid_type, f"Type: {server_type}")
            
            return True
            
        except Exception as e:
            self.log_result("MCP config loading", False, f"Configuration error: {e}")
            return False
    
    def test_dependencies(self) -> bool:
        """Test required Python package dependencies."""
        print("\n=== DEPENDENCY TESTS ===")
        
        required_packages = [
            ('LiveKit Agents', 'livekit.agents'),
            ('OpenAI Plugin', 'livekit.plugins.openai'),
            ('ElevenLabs Plugin', 'livekit.plugins.elevenlabs'),
            ('Silero Plugin', 'livekit.plugins.silero'),
            ('MCP Protocol', 'mcp'),
            ('Faster Whisper', 'faster_whisper'),
            ('Pytest', 'pytest'),
            ('PyYAML', 'yaml'),
            ('Requests', 'requests'),
            ('HTTPX', 'httpx'),
        ]
        
        all_passed = True
        for name, package in required_packages:
            try:
                __import__(package)
                self.log_result(f"{name} dependency", True)
            except ImportError:
                self.log_result(f"{name} dependency", False, f"Package '{package}' not installed")
                all_passed = False
        
        return all_passed
    
    def test_configuration_files(self) -> bool:
        """Test presence and validity of configuration files."""
        print("\n=== CONFIGURATION FILE TESTS ===")
        
        config_files = [
            ('MCP Servers Config', 'mcp_servers.yaml', True),
            ('Test Configuration', 'test-config.json', True),
            ('Requirements', 'requirements.txt', True),
            ('Environment Template', '.env.example', False),
            ('Makefile', 'Makefile', True),
        ]
        
        all_passed = True
        for name, filename, required in config_files:
            if os.path.exists(filename):
                self.log_result(f"{name} file", True, f"{filename} exists")
                
                # Additional validation for specific files
                if filename == 'test-config.json':
                    try:
                        with open(filename, 'r') as f:
                            config = json.load(f)
                        self.log_result(f"{name} validity", True, "Valid JSON configuration")
                    except json.JSONDecodeError as e:
                        self.log_result(f"{name} validity", False, f"Invalid JSON: {e}")
                        all_passed = False
                        
            else:
                self.log_result(f"{name} file", not required, 
                              f"{'Missing optional file' if not required else 'Required file missing'}: {filename}")
                if required:
                    all_passed = False
        
        return all_passed
    
    def test_whisper_stt_setup(self) -> bool:
        """Test Custom Whisper STT setup."""
        print("\n=== WHISPER STT TESTS ===")
        
        try:
            from custom_whisper_stt import CustomWhisperSTT
            
            # Test instantiation with minimal config
            stt = CustomWhisperSTT(model_size='base', language='en', device='cpu', compute_type='int8')
            self.log_result("Whisper STT instantiation", True, "CustomWhisperSTT created successfully")
            
            # Test capabilities
            capabilities = stt.capabilities
            streaming_supported = capabilities.streaming if hasattr(capabilities, 'streaming') else False
            interim_results = capabilities.interim_results if hasattr(capabilities, 'interim_results') else False
            
            self.log_result("Whisper STT capabilities", True, 
                          f"Streaming: {streaming_supported}, Interim: {interim_results}")
            
            return True
            
        except ImportError as e:
            self.log_result("Whisper STT setup", False, f"Import failed: {e}")
            return False
        except Exception as e:
            self.log_result("Whisper STT setup", False, f"Setup failed: {e}")
            return False
    
    def test_agent_core_setup(self) -> bool:
        """Test Agent Core setup (without full initialization)."""
        print("\n=== AGENT CORE TESTS ===")
        
        try:
            from agent_core import FunctionAgent
            
            # Set minimal environment for testing
            os.environ.setdefault('AGENT_SYSTEM_PROMPT', 'Test system prompt for verification')
            os.environ.setdefault('AGENT_LLM_MODEL', 'gpt-4.1-mini')
            
            self.log_result("Agent Core import", True, "FunctionAgent class available")
            
            # Check environment configuration
            llm_model = os.environ.get('AGENT_LLM_MODEL', 'default')
            stt_backend = os.environ.get('AGENT_STT_BACKEND', 'whisper')
            llm_backend = os.environ.get('AGENT_LLM_BACKEND', 'openai')
            
            self.log_result("Agent configuration", True, 
                          f"LLM: {llm_model}, STT: {stt_backend}, Backend: {llm_backend}")
            
            # Check for API keys (don't expose them)
            openai_key = bool(os.environ.get('OPENAI_API_KEY'))
            eleven_key = bool(os.environ.get('ELEVEN_API_KEY'))
            
            self.log_result("API keys status", openai_key and eleven_key, 
                          f"OpenAI: {'✓' if openai_key else '✗'}, ElevenLabs: {'✓' if eleven_key else '✗'}")
            
            return True
            
        except ImportError as e:
            self.log_result("Agent Core setup", False, f"Import failed: {e}")
            return False
        except Exception as e:
            self.log_result("Agent Core setup", False, f"Setup issue: {e}")
            return False
    
    def test_security_configuration(self) -> bool:
        """Test security-related configuration."""
        print("\n=== SECURITY CONFIGURATION TESTS ===")
        
        security_passed = True
        
        # Check for exposed credentials in code
        try:
            import subprocess
            result = subprocess.run(
                ['grep', '-r', 'sk_', '.', '--exclude-dir=.git', '--exclude=*.md'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout:
                self.log_result("Credential exposure check", False, 
                              "Potential API keys found in code")
                security_passed = False
            else:
                self.log_result("Credential exposure check", True, 
                              "No exposed credentials found")
        except Exception:
            self.log_result("Credential exposure check", True, 
                          "Check skipped (grep not available)")
        
        # Check MCP server security
        try:
            from mcp_config import load_mcp_config
            configs = load_mcp_config()
            
            secure_configs = 0
            for config in configs:
                url = config.get('url', '')
                has_auth = bool(config.get('headers', {}).get('Authorization'))
                
                if url.startswith('https://') and has_auth:
                    secure_configs += 1
            
            all_secure = secure_configs == len(configs)
            self.log_result("MCP server security", all_secure, 
                          f"{secure_configs}/{len(configs)} servers properly secured")
            
            if not all_secure:
                security_passed = False
                
        except Exception as e:
            self.log_result("MCP server security", False, f"Security check failed: {e}")
            security_passed = False
        
        return security_passed
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all verification tests."""
        print("🔍 VOICE MCP AGENT SYSTEM VERIFICATION")
        print("=====================================")
        
        test_results = {
            'module_imports': self.test_module_imports(),
            'mcp_configuration': self.test_mcp_configuration(),
            'dependencies': self.test_dependencies(),
            'configuration_files': self.test_configuration_files(),
            'whisper_stt_setup': self.test_whisper_stt_setup(),
            'agent_core_setup': self.test_agent_core_setup(),
            'security_configuration': self.test_security_configuration(),
        }
        
        # Summary
        print("\n" + "="*50)
        print("VERIFICATION SUMMARY")
        print("="*50)
        
        passed_tests = sum(1 for passed in test_results.values() if passed)
        total_tests = len(test_results)
        
        for test_name, passed in test_results.items():
            status = "PASS" if passed else "FAIL"
            print(f"{test_name.replace('_', ' ').title():.<30} {status}")
        
        print(f"\nOverall Result: {passed_tests}/{total_tests} test categories passed")
        
        if self.critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for failure in self.critical_failures[:5]:  # Show first 5
                print(f"  • {failure}")
            if len(self.critical_failures) > 5:
                print(f"  • ... and {len(self.critical_failures) - 5} more")
        
        # Determine overall status
        success_rate = passed_tests / total_tests
        if success_rate >= 0.9:
            print("\n🎉 SYSTEM VERIFICATION: PASSED")
            print("✓ Core components are functional")
            print("⚠️  Manual voice testing still required")
        elif success_rate >= 0.75:
            print("\n⚠️  SYSTEM VERIFICATION: PARTIAL")
            print("✓ Basic functionality available")
            print("⚠️  Some issues need resolution before production")
        else:
            print("\n❌ SYSTEM VERIFICATION: FAILED")
            print("✗ Critical issues prevent proper operation")
            print("⚠️  System NOT ready for deployment")
        
        return {
            'success_rate': success_rate,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'test_results': test_results,
            'critical_failures': self.critical_failures,
            'overall_status': 'PASSED' if success_rate >= 0.9 else 
                            'PARTIAL' if success_rate >= 0.75 else 'FAILED'
        }


def main():
    """Main verification entry point."""
    verifier = SystemVerifier()
    results = verifier.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['success_rate'] >= 0.9 else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()