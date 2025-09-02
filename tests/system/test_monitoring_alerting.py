"""
Monitoring and Alerting Test Scenarios
Comprehensive testing of system monitoring, health checks, and alerting
"""

import pytest
import asyncio
import aiohttp
import json
import time
import psutil
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile
import logging
import subprocess
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Health check result container"""
    service: str
    status: str  # 'healthy', 'warning', 'critical'
    response_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class MetricsSnapshot:
    """System metrics snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    open_files: int
    connections: int

@dataclass
class AlertCondition:
    """Alert condition definition"""
    name: str
    metric: str
    operator: str  # '>', '<', '==', '!=', 'contains'
    threshold: float
    duration_seconds: int
    severity: str  # 'info', 'warning', 'critical'
    enabled: bool = True

class SystemMonitor:
    """System monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics_history: List[MetricsSnapshot] = []
        self.alert_conditions: List[AlertCondition] = []
        self.active_alerts: Dict[str, datetime] = {}
    
    def collect_metrics(self) -> MetricsSnapshot:
        """Collect current system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / 1024 / 1024
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        
        # Network I/O
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        # Process info
        try:
            open_files = len(psutil.Process().open_files())
            connections = len(psutil.net_connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            open_files = 0
            connections = 0
        
        snapshot = MetricsSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_usage_percent=disk_usage_percent,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            open_files=open_files,
            connections=connections
        )
        
        self.metrics_history.append(snapshot)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        return snapshot
    
    def add_alert_condition(self, condition: AlertCondition) -> None:
        """Add alert condition"""
        self.alert_conditions.append(condition)
    
    def check_alerts(self, current_metrics: MetricsSnapshot) -> List[Dict]:
        """Check alert conditions against current metrics"""
        alerts = []
        
        for condition in self.alert_conditions:
            if not condition.enabled:
                continue
            
            # Get metric value
            metric_value = getattr(current_metrics, condition.metric, None)
            if metric_value is None:
                continue
            
            # Check condition
            condition_met = False
            if condition.operator == '>':
                condition_met = metric_value > condition.threshold
            elif condition.operator == '<':
                condition_met = metric_value < condition.threshold
            elif condition.operator == '==':
                condition_met = metric_value == condition.threshold
            elif condition.operator == '!=':
                condition_met = metric_value != condition.threshold
            
            if condition_met:
                alert_key = f"{condition.name}:{condition.metric}"
                
                # Check if alert is already active
                if alert_key in self.active_alerts:
                    # Check if duration threshold is met
                    alert_duration = (current_metrics.timestamp - self.active_alerts[alert_key]).total_seconds()
                    if alert_duration >= condition.duration_seconds:
                        alerts.append({
                            'name': condition.name,
                            'metric': condition.metric,
                            'value': metric_value,
                            'threshold': condition.threshold,
                            'severity': condition.severity,
                            'duration': alert_duration,
                            'timestamp': current_metrics.timestamp.isoformat()
                        })
                else:
                    # Start tracking this condition
                    self.active_alerts[alert_key] = current_metrics.timestamp
            else:
                # Condition not met, remove from active alerts
                alert_key = f"{condition.name}:{condition.metric}"
                if alert_key in self.active_alerts:
                    del self.active_alerts[alert_key]
        
        return alerts
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict:
        """Get metrics summary for specified duration"""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages, mins, maxs
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'duration_minutes': duration_minutes,
            'sample_count': len(recent_metrics),
            'cpu_percent': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values)
            },
            'memory_percent': {
                'avg': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values)
            },
            'latest': asdict(recent_metrics[-1])
        }

class LiveKitHealthChecker:
    """Health checker for LiveKit services"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def setup(self):
        """Setup health checker"""
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        """Cleanup health checker"""
        if self.session:
            await self.session.close()
    
    async def check_livekit_health(self) -> HealthCheckResult:
        """Check LiveKit server health"""
        start_time = time.time()
        
        try:
            url = f"http://{self.config['livekit']['host']}:{self.config['livekit']['port']}/health"
            
            async with self.session.get(url, timeout=5) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return HealthCheckResult(
                        service='livekit',
                        status='healthy',
                        response_time_ms=response_time
                    )
                else:
                    return HealthCheckResult(
                        service='livekit',
                        status='warning',
                        response_time_ms=response_time,
                        error_message=f"HTTP {response.status}"
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service='livekit',
                status='critical',
                response_time_ms=5000,
                error_message="Health check timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                service='livekit',
                status='critical',
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis health"""
        start_time = time.time()
        
        try:
            redis_client = redis.Redis(
                host=self.config['redis']['host'],
                port=self.config['redis']['port']
            )
            
            result = await redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            await redis_client.aclose()
            
            if result:
                return HealthCheckResult(
                    service='redis',
                    status='healthy',
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    service='redis',
                    status='critical',
                    response_time_ms=response_time,
                    error_message="Redis ping failed"
                )
                
        except Exception as e:
            return HealthCheckResult(
                service='redis',
                status='critical',
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def check_caddy_health(self) -> HealthCheckResult:
        """Check Caddy proxy health"""
        start_time = time.time()
        
        try:
            # Check if Caddy is responding on configured domains
            test_url = f"http://{self.config['caddy']['host']}"
            
            async with self.session.get(test_url, timeout=5) as response:
                response_time = (time.time() - start_time) * 1000
                
                # Caddy might return various status codes depending on configuration
                if response.status in [200, 404, 502, 503]:
                    return HealthCheckResult(
                        service='caddy',
                        status='healthy',
                        response_time_ms=response_time
                    )
                else:
                    return HealthCheckResult(
                        service='caddy',
                        status='warning',
                        response_time_ms=response_time,
                        error_message=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                service='caddy',
                status='critical',
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def run_comprehensive_health_check(self) -> List[HealthCheckResult]:
        """Run health checks for all services"""
        health_checks = [
            self.check_livekit_health(),
            self.check_redis_health(),
            self.check_caddy_health()
        ]
        
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        # Convert exceptions to critical health results
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_names = ['livekit', 'redis', 'caddy']
                health_results.append(HealthCheckResult(
                    service=service_names[i],
                    status='critical',
                    response_time_ms=0,
                    error_message=str(result)
                ))
            else:
                health_results.append(result)
        
        return health_results

@pytest.fixture
async def monitoring_setup():
    """Fixture providing monitoring setup"""
    config = {
        'livekit': {
            'host': 'localhost',
            'port': 7880
        },
        'redis': {
            'host': 'localhost',
            'port': 6379
        },
        'caddy': {
            'host': 'lk.delo.sh',
            'port': 443
        },
        'test_mode': True
    }
    
    # Setup system monitor
    system_monitor = SystemMonitor()
    
    # Add default alert conditions
    system_monitor.add_alert_condition(AlertCondition(
        name='High CPU Usage',
        metric='cpu_percent',
        operator='>',
        threshold=80.0,
        duration_seconds=30,
        severity='warning'
    ))
    
    system_monitor.add_alert_condition(AlertCondition(
        name='High Memory Usage',
        metric='memory_percent',
        operator='>',
        threshold=90.0,
        duration_seconds=60,
        severity='critical'
    ))
    
    system_monitor.add_alert_condition(AlertCondition(
        name='High Disk Usage',
        metric='disk_usage_percent',
        operator='>',
        threshold=95.0,
        duration_seconds=300,
        severity='critical'
    ))
    
    # Setup health checker
    health_checker = LiveKitHealthChecker(config)
    await health_checker.setup()
    
    yield {
        'system_monitor': system_monitor,
        'health_checker': health_checker,
        'config': config
    }
    
    await health_checker.teardown()

class TestSystemMonitoring:
    """Test system monitoring functionality"""
    
    def test_metrics_collection(self, monitoring_setup):
        """Test system metrics collection"""
        monitor = monitoring_setup['system_monitor']
        
        # Collect metrics
        metrics = monitor.collect_metrics()
        
        # Validate metrics
        assert metrics.timestamp is not None
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_used_mb > 0
        assert 0 <= metrics.disk_usage_percent <= 100
        assert metrics.network_bytes_sent >= 0
        assert metrics.network_bytes_recv >= 0
        
        logger.info(f"Collected metrics: CPU={metrics.cpu_percent:.1f}%, Memory={metrics.memory_percent:.1f}%")
    
    def test_metrics_history_management(self, monitoring_setup):
        """Test metrics history management"""
        monitor = monitoring_setup['system_monitor']
        
        # Collect multiple metrics
        initial_count = len(monitor.metrics_history)
        
        for _ in range(10):
            monitor.collect_metrics()
            time.sleep(0.01)  # Small delay
        
        assert len(monitor.metrics_history) == initial_count + 10
        
        # Verify timestamps are ordered
        timestamps = [m.timestamp for m in monitor.metrics_history]
        assert timestamps == sorted(timestamps), "Metrics timestamps not in order"
        
        logger.info(f"Metrics history: {len(monitor.metrics_history)} entries")
    
    def test_alert_conditions(self, monitoring_setup):
        """Test alert condition evaluation"""
        monitor = monitoring_setup['system_monitor']
        
        # Add test alert condition with low threshold to trigger
        test_condition = AlertCondition(
            name='Test Low CPU Alert',
            metric='cpu_percent',
            operator='>',
            threshold=0.0,  # Very low threshold to trigger
            duration_seconds=0,  # Immediate trigger
            severity='info'
        )
        
        monitor.add_alert_condition(test_condition)
        
        # Collect metrics and check alerts
        metrics = monitor.collect_metrics()
        alerts = monitor.check_alerts(metrics)
        
        # Should have triggered the test alert
        test_alerts = [a for a in alerts if a['name'] == 'Test Low CPU Alert']
        assert len(test_alerts) > 0, "Test alert condition not triggered"
        
        test_alert = test_alerts[0]
        assert test_alert['severity'] == 'info'
        assert test_alert['metric'] == 'cpu_percent'
        assert test_alert['value'] > test_alert['threshold']
        
        logger.info(f"Test alert triggered: {test_alert['name']} = {test_alert['value']}")
    
    def test_alert_duration_threshold(self, monitoring_setup):
        """Test alert duration threshold functionality"""
        monitor = monitoring_setup['system_monitor']
        
        # Add condition with duration threshold
        duration_condition = AlertCondition(
            name='Duration Test Alert',
            metric='cpu_percent',
            operator='>',
            threshold=0.0,
            duration_seconds=2,  # 2 second threshold
            severity='warning'
        )
        
        monitor.add_alert_condition(duration_condition)
        
        # First check - should not trigger (duration not met)
        metrics1 = monitor.collect_metrics()
        alerts1 = monitor.check_alerts(metrics1)
        
        duration_alerts = [a for a in alerts1 if a['name'] == 'Duration Test Alert']
        assert len(duration_alerts) == 0, "Alert triggered before duration threshold"
        
        # Wait for duration threshold
        time.sleep(2.1)
        
        # Second check - should trigger now
        metrics2 = monitor.collect_metrics()
        alerts2 = monitor.check_alerts(metrics2)
        
        duration_alerts = [a for a in alerts2 if a['name'] == 'Duration Test Alert']
        assert len(duration_alerts) > 0, "Alert not triggered after duration threshold"
        
        logger.info(f"Duration threshold alert triggered after {duration_alerts[0]['duration']:.1f}s")
    
    def test_metrics_summary(self, monitoring_setup):
        """Test metrics summary generation"""
        monitor = monitoring_setup['system_monitor']
        
        # Collect several metrics
        for _ in range(5):
            monitor.collect_metrics()
            time.sleep(0.1)
        
        summary = monitor.get_metrics_summary(duration_minutes=1)
        
        assert 'sample_count' in summary
        assert summary['sample_count'] > 0
        assert 'cpu_percent' in summary
        assert 'memory_percent' in summary
        assert 'latest' in summary
        
        # Validate summary structure
        cpu_summary = summary['cpu_percent']
        assert 'avg' in cpu_summary
        assert 'min' in cpu_summary
        assert 'max' in cpu_summary
        
        logger.info(f"Metrics summary: {summary['sample_count']} samples, CPU avg={cpu_summary['avg']:.1f}%")

class TestHealthChecks:
    """Test health check functionality"""
    
    async def test_livekit_health_check(self, monitoring_setup):
        """Test LiveKit health check"""
        health_checker = monitoring_setup['health_checker']
        
        try:
            result = await health_checker.check_livekit_health()
            
            assert result.service == 'livekit'
            assert result.status in ['healthy', 'warning', 'critical']
            assert result.response_time_ms >= 0
            assert result.timestamp is not None
            
            logger.info(f"LiveKit health: {result.status} ({result.response_time_ms:.1f}ms)")
            
            if result.status == 'critical':
                logger.warning(f"LiveKit health critical: {result.error_message}")
                
        except Exception as e:
            pytest.skip(f"LiveKit health check failed: {e}")
    
    async def test_redis_health_check(self, monitoring_setup):
        """Test Redis health check"""
        health_checker = monitoring_setup['health_checker']
        
        try:
            result = await health_checker.check_redis_health()
            
            assert result.service == 'redis'
            assert result.status in ['healthy', 'warning', 'critical']
            assert result.response_time_ms >= 0
            
            logger.info(f"Redis health: {result.status} ({result.response_time_ms:.1f}ms)")
            
            if result.status == 'critical':
                logger.warning(f"Redis health critical: {result.error_message}")
                
        except Exception as e:
            pytest.skip(f"Redis health check failed: {e}")
    
    async def test_comprehensive_health_check(self, monitoring_setup):
        """Test comprehensive health check across all services"""
        health_checker = monitoring_setup['health_checker']
        
        results = await health_checker.run_comprehensive_health_check()
        
        assert len(results) >= 3, "Not all services checked"
        
        services_checked = {result.service for result in results}
        expected_services = {'livekit', 'redis', 'caddy'}
        assert services_checked >= expected_services, f"Missing services: {expected_services - services_checked}"
        
        # Log health status for all services
        for result in results:
            logger.info(f"Service {result.service}: {result.status} ({result.response_time_ms:.1f}ms)")
            if result.error_message:
                logger.warning(f"  Error: {result.error_message}")
        
        # Count healthy services
        healthy_services = sum(1 for result in results if result.status == 'healthy')
        logger.info(f"Healthy services: {healthy_services}/{len(results)}")
    
    async def test_health_check_timeout_handling(self, monitoring_setup):
        """Test health check timeout handling"""
        health_checker = monitoring_setup['health_checker']
        
        # Test with invalid host to trigger timeout
        original_host = health_checker.config['livekit']['host']
        health_checker.config['livekit']['host'] = '192.0.2.1'  # RFC 5737 test address (non-routable)
        
        try:
            result = await health_checker.check_livekit_health()
            
            assert result.service == 'livekit'
            assert result.status == 'critical'
            assert result.response_time_ms >= 5000  # Should hit timeout
            assert result.error_message is not None
            
            logger.info(f"Timeout handling test: {result.status}, {result.error_message}")
            
        finally:
            # Restore original host
            health_checker.config['livekit']['host'] = original_host
    
    async def test_health_check_performance(self, monitoring_setup):
        """Test health check performance"""
        health_checker = monitoring_setup['health_checker']
        
        # Run multiple health checks and measure performance
        iterations = 5
        start_time = time.time()
        
        for _ in range(iterations):
            await health_checker.check_livekit_health()
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        # Health checks should be fast
        assert avg_time < 1.0, f"Health checks too slow: {avg_time:.3f}s average"
        
        logger.info(f"Health check performance: {avg_time:.3f}s average over {iterations} iterations")

class TestAlertingIntegration:
    """Test alerting integration and notification"""
    
    def test_alert_threshold_calculation(self, monitoring_setup):
        """Test alert threshold calculations"""
        monitor = monitoring_setup['system_monitor']
        
        # Test different operators
        test_cases = [
            (50.0, '>', 40.0, True),   # 50 > 40
            (30.0, '>', 40.0, False),  # 30 > 40
            (40.0, '<', 50.0, True),   # 40 < 50
            (60.0, '<', 50.0, False),  # 60 < 50
            (50.0, '==', 50.0, True),  # 50 == 50
            (50.0, '!=', 60.0, True),  # 50 != 60
        ]
        
        for value, operator, threshold, expected in test_cases:
            condition = AlertCondition(
                name='Test Condition',
                metric='cpu_percent',
                operator=operator,
                threshold=threshold,
                duration_seconds=0,
                severity='info'
            )
            
            # Create mock metrics
            from datetime import datetime
            mock_metrics = MetricsSnapshot(
                timestamp=datetime.utcnow(),
                cpu_percent=value,
                memory_percent=50.0,
                memory_used_mb=1000.0,
                disk_usage_percent=50.0,
                network_bytes_sent=1000,
                network_bytes_recv=1000,
                open_files=10,
                connections=5
            )
            
            monitor.alert_conditions = [condition]
            monitor.active_alerts = {}
            
            alerts = monitor.check_alerts(mock_metrics)
            
            if expected:
                assert len(alerts) > 0, f"Expected alert for {value} {operator} {threshold}"
            else:
                assert len(alerts) == 0, f"Unexpected alert for {value} {operator} {threshold}"
        
        logger.info("Alert threshold calculations validated")
    
    def test_alert_severity_levels(self, monitoring_setup):
        """Test different alert severity levels"""
        monitor = monitoring_setup['system_monitor']
        
        severity_conditions = [
            ('Info Alert', 'info'),
            ('Warning Alert', 'warning'), 
            ('Critical Alert', 'critical')
        ]
        
        # Add conditions for each severity level
        for name, severity in severity_conditions:
            condition = AlertCondition(
                name=name,
                metric='cpu_percent',
                operator='>',
                threshold=0.0,  # Will trigger
                duration_seconds=0,
                severity=severity
            )
            monitor.add_alert_condition(condition)
        
        # Trigger alerts
        metrics = monitor.collect_metrics()
        alerts = monitor.check_alerts(metrics)
        
        # Verify all severity levels present
        severities_found = {alert['severity'] for alert in alerts}
        expected_severities = {'info', 'warning', 'critical'}
        
        assert severities_found >= expected_severities, f"Missing severities: {expected_severities - severities_found}"
        
        logger.info(f"Alert severities tested: {sorted(severities_found)}")
    
    async def test_alert_notification_formatting(self, monitoring_setup):
        """Test alert notification message formatting"""
        monitor = monitoring_setup['system_monitor']
        
        # Add test condition
        condition = AlertCondition(
            name='Test Formatting Alert',
            metric='memory_percent',
            operator='>',
            threshold=50.0,
            duration_seconds=0,
            severity='warning'
        )
        monitor.add_alert_condition(condition)
        
        # Trigger alert
        metrics = monitor.collect_metrics()
        alerts = monitor.check_alerts(metrics)
        
        if alerts:
            alert = alerts[0]
            
            # Validate alert format
            required_fields = ['name', 'metric', 'value', 'threshold', 'severity', 'timestamp']
            for field in required_fields:
                assert field in alert, f"Missing field in alert: {field}"
            
            # Test notification message formatting
            message = f"ALERT: {alert['name']}\n"
            message += f"Metric: {alert['metric']} = {alert['value']:.1f}\n"
            message += f"Threshold: {alert['threshold']}\n"
            message += f"Severity: {alert['severity'].upper()}\n"
            message += f"Time: {alert['timestamp']}"
            
            assert len(message) > 0
            assert alert['name'] in message
            assert str(alert['value']) in message
            
            logger.info(f"Alert notification formatted:\n{message}")

class TestMonitoringPerformance:
    """Test monitoring system performance"""
    
    def test_metrics_collection_performance(self, monitoring_setup):
        """Test performance of metrics collection"""
        monitor = monitoring_setup['system_monitor']
        
        # Measure metrics collection time
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            monitor.collect_metrics()
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        # Metrics collection should be fast
        assert avg_time < 0.01, f"Metrics collection too slow: {avg_time:.4f}s average"
        
        logger.info(f"Metrics collection performance: {avg_time:.4f}s average")
    
    def test_alert_evaluation_performance(self, monitoring_setup):
        """Test performance of alert evaluation"""
        monitor = monitoring_setup['system_monitor']
        
        # Add many alert conditions
        for i in range(50):
            condition = AlertCondition(
                name=f'Test Alert {i}',
                metric='cpu_percent',
                operator='>',
                threshold=float(i),
                duration_seconds=0,
                severity='info'
            )
            monitor.add_alert_condition(condition)
        
        # Measure alert evaluation time
        metrics = monitor.collect_metrics()
        
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            monitor.check_alerts(metrics)
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        # Alert evaluation should be fast even with many conditions
        assert avg_time < 0.01, f"Alert evaluation too slow: {avg_time:.4f}s average"
        
        logger.info(f"Alert evaluation performance: {avg_time:.4f}s average with 50 conditions")
    
    async def test_concurrent_health_checks(self, monitoring_setup):
        """Test concurrent health check performance"""
        health_checker = monitoring_setup['health_checker']
        
        # Run concurrent health checks
        concurrent_checks = 10
        
        async def run_health_check():
            return await health_checker.check_livekit_health()
        
        start_time = time.time()
        
        tasks = [run_health_check() for _ in range(concurrent_checks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Concurrent checks should be faster than sequential
        assert total_time < concurrent_checks * 1.0, f"Concurrent health checks not efficient: {total_time:.2f}s"
        
        # Validate results
        successful_checks = sum(1 for result in results if not isinstance(result, Exception))
        logger.info(f"Concurrent health checks: {successful_checks}/{concurrent_checks} successful in {total_time:.2f}s")

@pytest.mark.asyncio
async def test_monitoring_integration():
    """Integration test for complete monitoring system"""
    # Setup
    config = {
        'livekit': {'host': 'localhost', 'port': 7880},
        'redis': {'host': 'localhost', 'port': 6379},
        'caddy': {'host': 'lk.delo.sh', 'port': 443},
        'test_mode': True
    }
    
    monitor = SystemMonitor()
    health_checker = LiveKitHealthChecker(config)
    await health_checker.setup()
    
    try:
        # Collect metrics
        metrics = monitor.collect_metrics()
        assert metrics is not None
        
        # Run health checks
        health_results = await health_checker.run_comprehensive_health_check()
        assert len(health_results) > 0
        
        # Generate metrics summary
        summary = monitor.get_metrics_summary()
        
        logger.info(f"Integration test completed: {len(health_results)} services checked")
        
    finally:
        await health_checker.teardown()

if __name__ == "__main__":
    # Run monitoring and alerting tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])