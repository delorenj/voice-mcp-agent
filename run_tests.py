#!/usr/bin/env python3
"""
LiveKit Deployment Test Runner
Comprehensive test execution and reporting for LiveKit voice-MCP agent deployment
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test-execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Main test runner for LiveKit deployment validation"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.test_results: List[Dict] = []
        self.start_time = datetime.utcnow()
        
    def run_pytest_suite(self, test_path: str, markers: Optional[str] = None) -> Tuple[int, str]:
        """Run pytest test suite and return results"""
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file=reports/{Path(test_path).stem}-report.json",
            "--cov=.",
            f"--cov-report=html:reports/{Path(test_path).stem}-coverage",
            "--cov-report=term-missing"
        ]
        
        if markers:
            cmd.extend(["-m", markers])
        
        if self.config.get('parallel', False):
            cmd.extend(["-n", "auto"])
        
        try:
            logger.info(f"Running test suite: {test_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get('test_timeout', 300)
            )
            
            return result.returncode, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test suite {test_path} timed out")
            return 1, "Test suite timed out"
        except Exception as e:
            logger.error(f"Error running test suite {test_path}: {e}")
            return 1, str(e)
    
    def run_test_category(self, category: str, test_paths: List[str]) -> Dict:
        """Run a category of tests"""
        logger.info(f"Starting test category: {category}")
        category_start = time.time()
        
        category_results = {
            'category': category,
            'start_time': datetime.utcnow().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for test_path in test_paths:
            if not Path(test_path).exists():
                logger.warning(f"Test path does not exist: {test_path}")
                continue
                
            return_code, output = self.run_pytest_suite(test_path)
            
            test_result = {
                'path': test_path,
                'return_code': return_code,
                'passed': return_code == 0,
                'output': output[-2000] if len(output) > 2000 else output  # Truncate long outputs
            }
            
            category_results['tests'].append(test_result)
            
            if return_code == 0:
                passed_tests += 1
            else:
                failed_tests += 1
            
            total_tests += 1
        
        category_end = time.time()
        
        category_results.update({
            'end_time': datetime.utcnow().isoformat(),
            'duration_seconds': category_end - category_start,
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        })
        
        logger.info(f"Category {category} completed: {passed_tests}/{total_tests} passed")
        return category_results
    
    def validate_environment(self) -> bool:
        """Validate test environment prerequisites"""
        logger.info("Validating test environment...")
        
        # Check required directories exist
        required_dirs = ['tests', 'tests/unit', 'tests/integration', 'tests/system']
        for directory in required_dirs:
            if not Path(directory).exists():
                logger.error(f"Required directory missing: {directory}")
                return False
        
        # Check required Python packages
        required_packages = ['pytest', 'pytest-asyncio', 'pytest-cov', 'aiohttp', 'redis']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"Missing required packages: {missing_packages}")
            logger.info("Install with: pip install " + " ".join(missing_packages))
            return False
        
        # Create reports directory
        Path("reports").mkdir(exist_ok=True)
        
        logger.info("Environment validation passed")
        return True
    
    def run_all_tests(self) -> Dict:
        """Run complete test suite"""
        if not self.validate_environment():
            logger.error("Environment validation failed")
            sys.exit(1)
        
        logger.info("Starting comprehensive test execution")
        
        # Define test categories and paths
        test_categories = {
            'unit': [
                'tests/unit/test_agent_config.py',
                'tests/unit/test_custom_whisper.py',
                'tests/unit/test_mcp_config.py'
            ],
            'integration': [
                'tests/integration/test_livekit_stack.py',
                'tests/integration/test_ssl_tls_validation.py', 
                'tests/integration/test_mcp_integration.py'
            ],
            'system': [
                'tests/system/test_media_streaming.py',
                'tests/system/test_monitoring_alerting.py'
            ],
            'performance': [
                'tests/performance/test_load_testing.py',
                'tests/performance/test_stress_testing.py'
            ] if self.config.get('run_performance_tests', False) else []
        }
        
        # Execute test categories
        all_results = {
            'execution_id': f"test-run-{int(time.time())}",
            'start_time': self.start_time.isoformat(),
            'config': self.config,
            'categories': {},
            'overall_summary': {}
        }
        
        total_categories = 0
        passed_categories = 0
        
        for category, test_paths in test_categories.items():
            if not test_paths:  # Skip empty categories
                continue
                
            category_result = self.run_test_category(category, test_paths)
            all_results['categories'][category] = category_result
            
            total_categories += 1
            if category_result['summary']['failed'] == 0:
                passed_categories += 1
        
        # Calculate overall summary
        end_time = datetime.utcnow()
        total_duration = (end_time - self.start_time).total_seconds()
        
        all_test_results = []
        for category_result in all_results['categories'].values():
            all_test_results.extend(category_result['tests'])
        
        total_tests = len(all_test_results)
        passed_tests = sum(1 for test in all_test_results if test['passed'])
        failed_tests = total_tests - passed_tests
        
        all_results.update({
            'end_time': end_time.isoformat(),
            'duration_seconds': total_duration,
            'overall_summary': {
                'categories': {
                    'total': total_categories,
                    'passed': passed_categories,
                    'failed': total_categories - passed_categories
                },
                'tests': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
                }
            }
        })
        
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate comprehensive test report"""
        report_path = f"reports/test-report-{results['execution_id']}.json"
        
        # Save detailed JSON report
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate summary report
        summary_path = f"reports/test-summary-{results['execution_id']}.md"
        
        with open(summary_path, 'w') as f:
            f.write(f"# LiveKit Deployment Test Report\n\n")
            f.write(f"**Execution ID:** {results['execution_id']}\n")
            f.write(f"**Start Time:** {results['start_time']}\n")
            f.write(f"**End Time:** {results['end_time']}\n")
            f.write(f"**Duration:** {results['duration_seconds']:.2f} seconds\n\n")
            
            # Overall Summary
            f.write(f"## Overall Summary\n\n")
            summary = results['overall_summary']
            f.write(f"- **Total Tests:** {summary['tests']['total']}\n")
            f.write(f"- **Passed:** {summary['tests']['passed']} ({summary['tests']['success_rate']:.1f}%)\n")
            f.write(f"- **Failed:** {summary['tests']['failed']}\n\n")
            
            if summary['tests']['success_rate'] >= 90:
                f.write("🟢 **DEPLOYMENT READY** - Test success rate >= 90%\n\n")
            elif summary['tests']['success_rate'] >= 75:
                f.write("🟡 **DEPLOYMENT WITH CAUTION** - Some tests failing\n\n")
            else:
                f.write("🔴 **DEPLOYMENT NOT RECOMMENDED** - High failure rate\n\n")
            
            # Category Details
            f.write(f"## Test Categories\n\n")
            
            for category_name, category_result in results['categories'].items():
                status = "✅" if category_result['summary']['failed'] == 0 else "❌"
                f.write(f"### {status} {category_name.title()} Tests\n\n")
                f.write(f"- **Tests:** {category_result['summary']['total']}\n")
                f.write(f"- **Passed:** {category_result['summary']['passed']}\n")
                f.write(f"- **Failed:** {category_result['summary']['failed']}\n")
                f.write(f"- **Success Rate:** {category_result['summary']['success_rate']:.1f}%\n")
                f.write(f"- **Duration:** {category_result['duration_seconds']:.2f}s\n\n")
                
                # List failed tests
                failed_tests = [test for test in category_result['tests'] if not test['passed']]
                if failed_tests:
                    f.write(f"**Failed Tests:**\n")
                    for test in failed_tests:
                        f.write(f"- {test['path']}\n")
                    f.write("\n")
            
            # Recommendations
            f.write(f"## Recommendations\n\n")
            
            if summary['tests']['success_rate'] >= 95:
                f.write("- Excellent test coverage and success rate\n")
                f.write("- Deployment is recommended\n")
                f.write("- Consider production rollout\n")
            elif summary['tests']['success_rate'] >= 90:
                f.write("- Good test success rate\n")  
                f.write("- Review failed tests before deployment\n")
                f.write("- Consider staged rollout\n")
            elif summary['tests']['success_rate'] >= 75:
                f.write("- Several test failures detected\n")
                f.write("- Address critical failures before deployment\n")
                f.write("- Additional testing recommended\n")
            else:
                f.write("- High number of test failures\n")
                f.write("- Do not deploy until issues are resolved\n")
                f.write("- Review system configuration and dependencies\n")
            
            f.write(f"\n---\n\n")
            f.write(f"*Report generated on {datetime.utcnow().isoformat()}*\n")
        
        logger.info(f"Test report generated: {summary_path}")
        return summary_path

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LiveKit Deployment Test Runner")
    parser.add_argument('--config', '-c', default='test-config.json', 
                       help='Test configuration file')
    parser.add_argument('--category', choices=['unit', 'integration', 'system', 'performance'],
                       help='Run specific test category only')
    parser.add_argument('--parallel', action='store_true',
                       help='Run tests in parallel')
    parser.add_argument('--performance', action='store_true',
                       help='Include performance tests')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Test timeout in seconds')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'parallel': args.parallel,
        'run_performance_tests': args.performance,
        'test_timeout': args.timeout,
        'verbose': args.verbose
    }
    
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            file_config = json.load(f)
            config.update(file_config)
    
    # Initialize test runner
    runner = TestRunner(config)
    
    try:
        if args.category:
            # Run single category
            test_categories = {
                'unit': ['tests/unit'],
                'integration': ['tests/integration'],
                'system': ['tests/system'],
                'performance': ['tests/performance']
            }
            
            if args.category in test_categories:
                category_result = runner.run_test_category(args.category, test_categories[args.category])
                print(f"\nCategory {args.category}: {category_result['summary']}")
            else:
                logger.error(f"Unknown test category: {args.category}")
                sys.exit(1)
        else:
            # Run all tests
            results = runner.run_all_tests()
            
            # Generate report
            report_path = runner.generate_report(results)
            
            # Print summary
            summary = results['overall_summary']
            print(f"\n{'='*60}")
            print(f"LIVEKIT DEPLOYMENT TEST RESULTS")
            print(f"{'='*60}")
            print(f"Total Tests: {summary['tests']['total']}")
            print(f"Passed: {summary['tests']['passed']} ({summary['tests']['success_rate']:.1f}%)")
            print(f"Failed: {summary['tests']['failed']}")
            print(f"Duration: {results['duration_seconds']:.2f} seconds")
            print(f"\nReport: {report_path}")
            
            # Exit with appropriate code
            if summary['tests']['failed'] == 0:
                print("\n🎉 ALL TESTS PASSED - DEPLOYMENT READY!")
                sys.exit(0)
            elif summary['tests']['success_rate'] >= 75:
                print(f"\n⚠️  SOME TESTS FAILED - REVIEW BEFORE DEPLOYMENT")
                sys.exit(1)
            else:
                print(f"\n❌ MANY TESTS FAILED - DO NOT DEPLOY")
                sys.exit(2)
                
    except KeyboardInterrupt:
        logger.info("Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()