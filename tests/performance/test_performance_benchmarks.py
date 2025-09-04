#!/usr/bin/env python3
"""
Performance Benchmarking Suite
Comprehensive performance testing and benchmarking for Mac Bridge system
"""

import asyncio
import json
import logging
import pytest
import websockets
import time
import psutil
import statistics
import concurrent.futures
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import tempfile
import os
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: float
    response_time: float
    memory_usage_mb: float
    cpu_percent: float
    network_io_bytes: int
    active_connections: int
    success_rate: float
    throughput_msgs_per_sec: float

class PerformanceBenchmarkTester:
    """Performance benchmark tester for Mac Bridge system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.websocket_url = config.get('websocket_url', 'wss://localhost:443/ws')
        self.metrics_history: List[PerformanceMetrics] = []
        self.test_results: List[Dict] = []
        
    async def create_test_connection(self, client_id: str) -> websockets.WebSocketClientProtocol:
        """Create a test WebSocket connection"""
        return await websockets.connect(
            self.websocket_url,
            extra_headers={'User-Agent': f'Performance-Test-Client/{client_id}'},
            ping_interval=20,
            ping_timeout=10
        )
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system performance metrics"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        network_io = psutil.net_io_counters()
        
        return {
            'timestamp': time.time(),
            'memory_usage_mb': memory.used / (1024 * 1024),
            'memory_percent': memory.percent,
            'cpu_percent': cpu_percent,
            'network_bytes_sent': network_io.bytes_sent,
            'network_bytes_recv': network_io.bytes_recv,
            'available_memory_mb': memory.available / (1024 * 1024)
        }
    
    async def benchmark_response_latency(self, num_requests: int = 100) -> Dict[str, Any]:
        """Benchmark response latency for individual requests"""
        test_start = time.time()
        test_result = {
            'test_name': 'response_latency_benchmark',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        connection = None
        latencies = []
        
        try:
            connection = await self.create_test_connection('latency_test')
            
            # Warm up
            warmup_message = {'type': 'warmup', 'data': 'test'}
            await connection.send(json.dumps(warmup_message))
            await connection.recv()
            
            logger.info(f"Starting latency benchmark with {num_requests} requests")
            
            for i in range(num_requests):
                request_start = time.time()
                
                # Send test message
                test_message = {
                    'type': 'latency_test',
                    'request_id': i,
                    'timestamp': request_start,
                    'data': f'latency_benchmark_request_{i}'
                }
                
                await connection.send(json.dumps(test_message))
                response = await connection.recv()
                
                request_end = time.time()
                latency = (request_end - request_start) * 1000  # Convert to milliseconds
                latencies.append(latency)
                
                # Small delay to avoid overwhelming the server
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # Calculate statistics
            stats = {
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'avg_latency_ms': statistics.mean(latencies),
                'median_latency_ms': statistics.median(latencies),
                'p95_latency_ms': np.percentile(latencies, 95),
                'p99_latency_ms': np.percentile(latencies, 99),
                'std_dev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                'total_requests': len(latencies),
                'successful_requests': len(latencies),
                'success_rate': 100.0
            }
            
            # Performance rating
            avg_latency = stats['avg_latency_ms']
            performance_rating = (
                'excellent' if avg_latency < 50 else
                'good' if avg_latency < 100 else
                'acceptable' if avg_latency < 200 else
                'poor'
            )
            
            test_result.update({
                'success': True,
                'details': {
                    'latency_statistics': stats,
                    'performance_rating': performance_rating,
                    'latency_distribution': {
                        'under_50ms': sum(1 for l in latencies if l < 50),
                        'under_100ms': sum(1 for l in latencies if l < 100),
                        'under_200ms': sum(1 for l in latencies if l < 200),
                        'over_200ms': sum(1 for l in latencies if l >= 200)
                    }
                }
            })
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Response latency benchmark failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def benchmark_concurrent_throughput(self, concurrent_clients: int = 20, 
                                            duration_seconds: int = 60) -> Dict[str, Any]:
        """Benchmark system throughput with concurrent clients"""
        test_start = time.time()
        test_result = {
            'test_name': 'concurrent_throughput_benchmark',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        connections = []
        results = []
        metrics_collection = []
        
        try:
            logger.info(f"Starting throughput benchmark: {concurrent_clients} clients for {duration_seconds}s")
            
            # Create concurrent connections
            connections = await asyncio.gather(*[
                self.create_test_connection(f'throughput_client_{i}')
                for i in range(concurrent_clients)
            ])
            
            # Start metrics collection
            metrics_stop_event = threading.Event()
            metrics_thread = threading.Thread(
                target=self._collect_metrics_continuously,
                args=(metrics_collection, metrics_stop_event, 1.0)  # 1 second intervals
            )
            metrics_thread.start()
            
            # Define client workload
            async def client_workload(connection, client_id):
                message_count = 0
                errors = 0
                start_time = time.time()
                
                while time.time() - start_time < duration_seconds:
                    try:
                        # Send message
                        message = {
                            'type': 'throughput_test',
                            'client_id': client_id,
                            'message_count': message_count,
                            'timestamp': time.time(),
                            'data': f'throughput_test_data_{message_count}'
                        }
                        
                        await connection.send(json.dumps(message))
                        response = await asyncio.wait_for(connection.recv(), timeout=5.0)
                        
                        message_count += 1
                        
                        # Small delay to simulate realistic usage
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        errors += 1
                        logger.debug(f"Client {client_id} error: {e}")
                        await asyncio.sleep(0.5)  # Back off on error
                
                return {
                    'client_id': client_id,
                    'messages_sent': message_count,
                    'errors': errors,
                    'success_rate': (message_count / (message_count + errors) * 100) if (message_count + errors) > 0 else 0,
                    'messages_per_second': message_count / duration_seconds
                }
            
            # Run concurrent client workloads
            client_tasks = [
                client_workload(conn, f'client_{i}')
                for i, conn in enumerate(connections)
            ]
            
            results = await asyncio.gather(*client_tasks, return_exceptions=True)
            
            # Stop metrics collection
            metrics_stop_event.set()
            metrics_thread.join()
            
            # Filter successful results
            successful_results = [
                r for r in results 
                if not isinstance(r, Exception)
            ]
            
            if successful_results:
                total_messages = sum(r['messages_sent'] for r in successful_results)
                total_errors = sum(r['errors'] for r in successful_results)
                overall_throughput = total_messages / duration_seconds
                overall_success_rate = sum(r['success_rate'] for r in successful_results) / len(successful_results)
                
                # Calculate metrics statistics
                if metrics_collection:
                    avg_memory = statistics.mean(m['memory_usage_mb'] for m in metrics_collection)
                    max_memory = max(m['memory_usage_mb'] for m in metrics_collection)
                    avg_cpu = statistics.mean(m['cpu_percent'] for m in metrics_collection)
                    max_cpu = max(m['cpu_percent'] for m in metrics_collection)
                else:
                    avg_memory = max_memory = avg_cpu = max_cpu = 0
                
                test_result.update({
                    'success': overall_success_rate >= 90,  # 90% success rate required
                    'details': {
                        'concurrent_clients': len(successful_results),
                        'test_duration_seconds': duration_seconds,
                        'total_messages': total_messages,
                        'total_errors': total_errors,
                        'overall_throughput_mps': overall_throughput,
                        'overall_success_rate': overall_success_rate,
                        'avg_messages_per_client': total_messages / len(successful_results),
                        'system_resources': {
                            'avg_memory_usage_mb': avg_memory,
                            'max_memory_usage_mb': max_memory,
                            'avg_cpu_percent': avg_cpu,
                            'max_cpu_percent': max_cpu
                        },
                        'performance_rating': (
                            'excellent' if overall_throughput >= 100 and avg_cpu < 50 else
                            'good' if overall_throughput >= 50 and avg_cpu < 70 else
                            'acceptable' if overall_throughput >= 20 and avg_cpu < 90 else
                            'poor'
                        )
                    }
                })
            else:
                test_result['details']['error'] = 'No successful client results'
            
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Concurrent throughput benchmark failed: {e}")
        
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
    
    def _collect_metrics_continuously(self, metrics_list: List[Dict], 
                                    stop_event: threading.Event, interval: float):
        """Continuously collect system metrics in background thread"""
        while not stop_event.is_set():
            try:
                metrics = self.collect_system_metrics()
                metrics_list.append(metrics)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                break
    
    async def benchmark_voice_processing_latency(self, num_samples: int = 50) -> Dict[str, Any]:
        """Benchmark voice processing pipeline latency"""
        test_start = time.time()
        test_result = {
            'test_name': 'voice_processing_latency_benchmark',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        connection = None
        processing_times = []
        
        try:
            connection = await self.create_test_connection('voice_latency_test')
            
            # Generate synthetic audio data for testing
            sample_rate = 16000
            duration = 2.0  # 2 seconds
            
            logger.info(f"Starting voice processing latency benchmark with {num_samples} samples")
            
            for i in range(num_samples):
                # Create synthetic audio
                frequency = 440 + (i * 10)  # Vary frequency slightly
                t = np.linspace(0, duration, int(sample_rate * duration))
                audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
                
                # Convert to bytes
                audio_bytes = audio_data.tobytes()
                
                processing_start = time.time()
                
                # Send voice processing request
                voice_message = {
                    'type': 'voice_processing',
                    'sample_id': i,
                    'timestamp': processing_start,
                    'audio_format': 'raw_float32',
                    'sample_rate': sample_rate,
                    'duration': duration,
                    'audio_data': audio_bytes.hex()
                }
                
                await connection.send(json.dumps(voice_message))
                response = await asyncio.wait_for(connection.recv(), timeout=30.0)
                
                processing_end = time.time()
                processing_time = (processing_end - processing_start) * 1000  # milliseconds
                processing_times.append(processing_time)
                
                # Parse response to check if processing was successful
                try:
                    response_data = json.loads(response)
                    if 'error' in response_data:
                        logger.warning(f"Voice processing sample {i} had error: {response_data['error']}")
                except:
                    pass
                
                # Delay between samples
                await asyncio.sleep(0.5)
            
            # Calculate statistics
            if processing_times:
                stats = {
                    'min_processing_ms': min(processing_times),
                    'max_processing_ms': max(processing_times),
                    'avg_processing_ms': statistics.mean(processing_times),
                    'median_processing_ms': statistics.median(processing_times),
                    'p95_processing_ms': np.percentile(processing_times, 95),
                    'p99_processing_ms': np.percentile(processing_times, 99),
                    'std_dev_ms': statistics.stdev(processing_times) if len(processing_times) > 1 else 0,
                    'total_samples': len(processing_times),
                    'audio_duration_s': duration,
                    'real_time_factor': statistics.mean(processing_times) / (duration * 1000)  # Should be < 1 for real-time
                }
                
                # Performance evaluation
                avg_processing = stats['avg_processing_ms']
                real_time_factor = stats['real_time_factor']
                
                performance_rating = (
                    'excellent' if avg_processing < 500 and real_time_factor < 0.25 else
                    'good' if avg_processing < 1000 and real_time_factor < 0.5 else
                    'acceptable' if avg_processing < 2000 and real_time_factor < 1.0 else
                    'poor'
                )
                
                test_result.update({
                    'success': real_time_factor < 1.0,  # Must be faster than real-time
                    'details': {
                        'processing_statistics': stats,
                        'performance_rating': performance_rating,
                        'real_time_capable': real_time_factor < 1.0,
                        'processing_distribution': {
                            'under_500ms': sum(1 for t in processing_times if t < 500),
                            'under_1000ms': sum(1 for t in processing_times if t < 1000),
                            'under_2000ms': sum(1 for t in processing_times if t < 2000),
                            'over_2000ms': sum(1 for t in processing_times if t >= 2000)
                        }
                    }
                })
            else:
                test_result['details']['error'] = 'No processing time samples collected'
                
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Voice processing latency benchmark failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def benchmark_memory_usage_pattern(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """Benchmark memory usage patterns over time"""
        test_start = time.time()
        test_result = {
            'test_name': 'memory_usage_pattern_benchmark',
            'start_time': datetime.utcnow().isoformat(),
            'success': False,
            'details': {}
        }
        
        duration_seconds = duration_minutes * 60
        memory_samples = []
        connection = None
        
        try:
            connection = await self.create_test_connection('memory_pattern_test')
            
            logger.info(f"Starting memory usage pattern benchmark for {duration_minutes} minutes")
            
            # Sample memory usage continuously
            sample_interval = 5.0  # 5 seconds
            samples_needed = int(duration_seconds / sample_interval)
            
            for i in range(samples_needed):
                sample_start = time.time()
                
                # Collect memory metrics
                metrics = self.collect_system_metrics()
                memory_samples.append({
                    'timestamp': metrics['timestamp'],
                    'memory_usage_mb': metrics['memory_usage_mb'],
                    'memory_percent': metrics['memory_percent'],
                    'available_memory_mb': metrics['available_memory_mb']
                })
                
                # Send test message to maintain activity
                test_message = {
                    'type': 'memory_pattern_test',
                    'sample_id': i,
                    'timestamp': sample_start,
                    'data': f'memory_test_sample_{i}'
                }
                
                try:
                    await connection.send(json.dumps(test_message))
                    await asyncio.wait_for(connection.recv(), timeout=3.0)
                except Exception as e:
                    logger.debug(f"Message {i} failed: {e}")
                
                # Wait for next sample
                elapsed = time.time() - sample_start
                sleep_time = max(0, sample_interval - elapsed)
                await asyncio.sleep(sleep_time)
            
            # Analyze memory patterns
            if memory_samples:
                memory_usage_values = [s['memory_usage_mb'] for s in memory_samples]
                memory_percent_values = [s['memory_percent'] for s in memory_samples]
                
                memory_stats = {
                    'min_usage_mb': min(memory_usage_values),
                    'max_usage_mb': max(memory_usage_values),
                    'avg_usage_mb': statistics.mean(memory_usage_values),
                    'memory_growth_mb': memory_usage_values[-1] - memory_usage_values[0],
                    'min_percent': min(memory_percent_values),
                    'max_percent': max(memory_percent_values),
                    'avg_percent': statistics.mean(memory_percent_values),
                    'std_dev_mb': statistics.stdev(memory_usage_values) if len(memory_usage_values) > 1 else 0,
                    'samples_collected': len(memory_samples)
                }
                
                # Detect memory leaks (significant upward trend)
                memory_leak_detected = memory_stats['memory_growth_mb'] > 100  # >100MB growth
                memory_stable = memory_stats['std_dev_mb'] < 50  # <50MB standard deviation
                
                test_result.update({
                    'success': not memory_leak_detected and memory_stats['max_percent'] < 90,
                    'details': {
                        'memory_statistics': memory_stats,
                        'memory_leak_detected': memory_leak_detected,
                        'memory_stable': memory_stable,
                        'test_duration_minutes': duration_minutes,
                        'sample_interval_seconds': sample_interval,
                        'memory_health': (
                            'excellent' if memory_stable and memory_stats['avg_percent'] < 50 else
                            'good' if memory_stable and memory_stats['avg_percent'] < 70 else
                            'acceptable' if not memory_leak_detected and memory_stats['avg_percent'] < 85 else
                            'poor'
                        )
                    }
                })
                
                # Generate simple memory usage graph data for reporting
                if len(memory_samples) > 1:
                    timestamps = [s['timestamp'] - memory_samples[0]['timestamp'] for s in memory_samples]
                    test_result['details']['memory_graph_data'] = {
                        'time_seconds': timestamps,
                        'memory_usage_mb': memory_usage_values,
                        'memory_percent': memory_percent_values
                    }
            else:
                test_result['details']['error'] = 'No memory samples collected'
                
        except Exception as e:
            test_result['details']['error'] = str(e)
            logger.error(f"Memory usage pattern benchmark failed: {e}")
        
        finally:
            if connection:
                await connection.close()
        
        test_result['end_time'] = datetime.utcnow().isoformat()
        test_result['duration'] = time.time() - test_start
        return test_result
    
    async def run_comprehensive_performance_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmark suite"""
        suite_start = time.time()
        
        results = {
            'benchmark_suite': 'performance_benchmarks',
            'start_time': datetime.utcnow().isoformat(),
            'benchmarks': [],
            'summary': {}
        }
        
        # Define benchmark sequence
        benchmarks = [
            ('response_latency', lambda: self.benchmark_response_latency(100)),
            ('concurrent_throughput', lambda: self.benchmark_concurrent_throughput(10, 30)),  # Smaller for CI
            ('voice_processing', lambda: self.benchmark_voice_processing_latency(20)),  # Smaller for CI
            ('memory_pattern', lambda: self.benchmark_memory_usage_pattern(2))  # 2 minutes for CI
        ]
        
        passed_benchmarks = 0
        failed_benchmarks = 0
        performance_scores = []
        
        for benchmark_name, benchmark_func in benchmarks:
            logger.info(f"Running performance benchmark: {benchmark_name}")
            
            try:
                benchmark_result = await benchmark_func()
                results['benchmarks'].append(benchmark_result)
                
                if benchmark_result['success']:
                    passed_benchmarks += 1
                    
                    # Extract performance rating for overall score
                    details = benchmark_result.get('details', {})
                    rating = details.get('performance_rating', 'unknown')
                    
                    rating_scores = {'excellent': 4, 'good': 3, 'acceptable': 2, 'poor': 1}
                    performance_scores.append(rating_scores.get(rating, 1))
                    
                    logger.info(f"✅ {benchmark_name} PASSED - Rating: {rating}")
                else:
                    failed_benchmarks += 1
                    performance_scores.append(1)  # Poor score for failed benchmark
                    logger.error(f"❌ {benchmark_name} FAILED")
                    
                # Delay between benchmarks to let system stabilize
                await asyncio.sleep(5)
                
            except Exception as e:
                failed_benchmarks += 1
                performance_scores.append(1)
                error_result = {
                    'test_name': benchmark_name,
                    'success': False,
                    'error': str(e),
                    'start_time': datetime.utcnow().isoformat(),
                    'end_time': datetime.utcnow().isoformat()
                }
                results['benchmarks'].append(error_result)
                logger.error(f"❌ {benchmark_name} FAILED with exception: {e}")
        
        # Calculate overall performance summary
        total_benchmarks = passed_benchmarks + failed_benchmarks
        success_rate = (passed_benchmarks / total_benchmarks * 100) if total_benchmarks > 0 else 0
        
        if performance_scores:
            avg_performance_score = statistics.mean(performance_scores)
            overall_performance_rating = (
                'excellent' if avg_performance_score >= 3.5 else
                'good' if avg_performance_score >= 2.5 else
                'acceptable' if avg_performance_score >= 1.5 else
                'poor'
            )
        else:
            avg_performance_score = 0
            overall_performance_rating = 'unknown'
        
        results.update({
            'end_time': datetime.utcnow().isoformat(),
            'duration': time.time() - suite_start,
            'summary': {
                'total_benchmarks': total_benchmarks,
                'passed': passed_benchmarks,
                'failed': failed_benchmarks,
                'success_rate': success_rate,
                'avg_performance_score': avg_performance_score,
                'overall_performance_rating': overall_performance_rating,
                'performance_acceptable': success_rate >= 75 and avg_performance_score >= 2.0
            }
        })
        
        return results

# Pytest test functions
@pytest.mark.asyncio
@pytest.mark.performance
async def test_response_latency_benchmark():
    """Test response latency performance"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = PerformanceBenchmarkTester(config)
    result = await tester.benchmark_response_latency(50)  # Smaller for CI
    
    assert result['success'], f"Response latency benchmark failed: {result.get('details', {}).get('error', 'Unknown error')}"
    
    # Assert performance requirements
    details = result.get('details', {})
    stats = details.get('latency_statistics', {})
    
    assert stats.get('avg_latency_ms', float('inf')) < 500, "Average latency too high"
    assert stats.get('p95_latency_ms', float('inf')) < 1000, "95th percentile latency too high"

@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_throughput_benchmark():
    """Test concurrent throughput performance"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = PerformanceBenchmarkTester(config)
    result = await tester.benchmark_concurrent_throughput(5, 15)  # Smaller for CI
    
    assert result['success'], f"Concurrent throughput benchmark failed: {result.get('details', {}).get('error', 'Unknown error')}"
    
    # Assert throughput requirements
    details = result.get('details', {})
    assert details.get('overall_success_rate', 0) >= 90, "Success rate too low"
    assert details.get('overall_throughput_mps', 0) >= 10, "Throughput too low"

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
async def test_voice_processing_benchmark():
    """Test voice processing latency performance"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = PerformanceBenchmarkTester(config)
    result = await tester.benchmark_voice_processing_latency(10)  # Smaller for CI
    
    assert result['success'], f"Voice processing benchmark failed: {result.get('details', {}).get('error', 'Unknown error')}"

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
async def test_memory_usage_pattern():
    """Test memory usage pattern over time"""
    config = {
        'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
    }
    
    tester = PerformanceBenchmarkTester(config)
    result = await tester.benchmark_memory_usage_pattern(1)  # 1 minute for CI
    
    assert result['success'], f"Memory pattern benchmark failed: {result.get('details', {}).get('error', 'Unknown error')}"

if __name__ == "__main__":
    # Run comprehensive performance benchmarks
    async def main():
        config = {
            'websocket_url': os.getenv('TEST_WEBSOCKET_URL', 'wss://localhost:443/ws')
        }
        
        tester = PerformanceBenchmarkTester(config)
        results = await tester.run_comprehensive_performance_benchmarks()
        
        print(json.dumps(results, indent=2))
        
        performance_rating = results['summary']['overall_performance_rating']
        if results['summary']['performance_acceptable']:
            print(f"\n🎉 PERFORMANCE BENCHMARKS PASSED - Overall rating: {performance_rating.upper()}")
            exit(0)
        else:
            print(f"\n⚠️  PERFORMANCE BENCHMARKS SHOW CONCERNS - Overall rating: {performance_rating.upper()}")
            exit(1)
    
    asyncio.run(main())