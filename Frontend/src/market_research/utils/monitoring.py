"""
Comprehensive System Monitoring and Alerting for Data Analysis Agent

Provides performance monitoring, resource tracking, error rate monitoring,
and notification systems for the analysis workflows.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json

from .error_handling import error_monitor, performance_monitor, resource_monitor


logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    active_connections: int
    load_average: Optional[float] = None


@dataclass
class WorkflowMetrics:
    """Analysis workflow metrics"""
    timestamp: str
    workflow_id: str
    operation: str
    duration: float
    status: str  # success, failed, timeout
    document_size: Optional[int] = None
    chunk_count: Optional[int] = None
    token_usage: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_type: str  # system, workflow, error_rate
    condition: str  # gt, lt, eq
    threshold: float
    window_minutes: int
    severity: str  # low, medium, high, critical
    enabled: bool = True
    cooldown_minutes: int = 30


class MetricsCollector:
    """
    Collects system and application metrics
    """
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.system_metrics_history = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.workflow_metrics_history = deque(maxlen=10000)  # Last 10k workflows
        self.is_collecting = False
        self.collection_thread = None
    
    def start_collection(self):
        """Start metrics collection in background thread"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("Stopped metrics collection")
    
    def _collection_loop(self):
        """Main collection loop running in background thread"""
        while self.is_collecting:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                if system_metrics:
                    self.system_metrics_history.append(system_metrics)
                
                # Sleep until next collection
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                # Continue running even if metrics collection fails
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # Initialize default values
        cpu_percent = 0.0
        memory_percent = 0.0
        memory_used_mb = 0.0
        disk_usage_percent = 0.0
        connections = 0
        load_avg = None
        
        try:
            # CPU and memory (most reliable metrics)
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
            except Exception as e:
                logger.debug(f"CPU metrics unavailable: {e}")
            
            try:
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_mb = memory.used / (1024 * 1024)
            except Exception as e:
                logger.debug(f"Memory metrics unavailable: {e}")
            
            # Disk usage for current directory
            try:
                disk = psutil.disk_usage('.')
                disk_usage_percent = disk.percent
            except Exception as e:
                logger.debug(f"Disk metrics unavailable: {e}")
            
            # Network connections (with comprehensive permission handling)
            try:
                connections = len(psutil.net_connections())
            except (psutil.AccessDenied, PermissionError, OSError):
                # Fallback: count network interfaces instead
                try:
                    connections = len(psutil.net_if_stats())
                except Exception:
                    # Final fallback: use process connections
                    try:
                        process = psutil.Process()
                        connections = len(process.connections())
                    except Exception:
                        connections = 0
            
            # Load average (Unix-like systems only)
            try:
                load_avg = psutil.getloadavg()[0]  # 1-minute load average
            except (AttributeError, OSError):
                pass  # Not available on Windows
            
            return SystemMetrics(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                active_connections=connections,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                active_connections=connections,
                load_average=load_avg
            )
    
    def record_workflow_metrics(
        self,
        workflow_id: str,
        operation: str,
        duration: float,
        status: str,
        **kwargs
    ):
        """Record workflow execution metrics"""
        metrics = WorkflowMetrics(
            timestamp=datetime.utcnow().isoformat(),
            workflow_id=workflow_id,
            operation=operation,
            duration=duration,
            status=status,
            document_size=kwargs.get('document_size'),
            chunk_count=kwargs.get('chunk_count'),
            token_usage=kwargs.get('token_usage'),
            error_message=kwargs.get('error_message')
        )
        
        self.workflow_metrics_history.append(metrics)
    
    def get_system_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get system metrics summary for specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.system_metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate averages and peaks
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "sample_count": len(recent_metrics),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "latest": asdict(recent_metrics[-1]) if recent_metrics else None
        }
    
    def get_workflow_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get workflow metrics summary for specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        recent_workflows = [
            m for m in self.workflow_metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]
        
        if not recent_workflows:
            return {"error": "No workflow metrics available for the specified period"}
        
        # Analyze by status
        status_counts = defaultdict(int)
        durations_by_operation = defaultdict(list)
        
        for workflow in recent_workflows:
            status_counts[workflow.status] += 1
            durations_by_operation[workflow.operation].append(workflow.duration)
        
        # Calculate operation statistics
        operation_stats = {}
        for operation, durations in durations_by_operation.items():
            operation_stats[operation] = {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations)
            }
        
        return {
            "period_hours": hours,
            "total_workflows": len(recent_workflows),
            "status_breakdown": dict(status_counts),
            "success_rate": status_counts["success"] / len(recent_workflows) if recent_workflows else 0,
            "operation_stats": operation_stats
        }


class AlertManager:
    """
    Manages alert rules and notifications
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_handlers = []
    
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def add_notification_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add a notification handler function"""
        self.notification_handlers.append(handler)
    
    def check_alerts(self):
        """Check all alert rules and trigger notifications if needed"""
        current_time = datetime.utcnow()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            try:
                if self._should_check_rule(rule, current_time):
                    alert_triggered = self._evaluate_rule(rule)
                    
                    if alert_triggered:
                        self._trigger_alert(rule, current_time)
                    else:
                        # Clear alert if it was previously active
                        if rule.name in self.active_alerts:
                            self._clear_alert(rule.name, current_time)
                            
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")
    
    def _should_check_rule(self, rule: AlertRule, current_time: datetime) -> bool:
        """Check if enough time has passed since last alert for this rule"""
        if rule.name not in self.active_alerts:
            return True
        
        last_alert_time = self.active_alerts[rule.name]["timestamp"]
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        
        return current_time - last_alert_time > cooldown_period
    
    def _evaluate_rule(self, rule: AlertRule) -> bool:
        """Evaluate if an alert rule should trigger"""
        if rule.metric_type == "system":
            return self._evaluate_system_rule(rule)
        elif rule.metric_type == "workflow":
            return self._evaluate_workflow_rule(rule)
        elif rule.metric_type == "error_rate":
            return self._evaluate_error_rate_rule(rule)
        else:
            logger.warning(f"Unknown metric type for rule {rule.name}: {rule.metric_type}")
            return False
    
    def _evaluate_system_rule(self, rule: AlertRule) -> bool:
        """Evaluate system metric alert rule"""
        window_start = datetime.utcnow() - timedelta(minutes=rule.window_minutes)
        
        recent_metrics = [
            m for m in self.metrics_collector.system_metrics_history
            if datetime.fromisoformat(m.timestamp) > window_start
        ]
        
        if not recent_metrics:
            return False
        
        # Get the metric value based on rule name
        if "cpu" in rule.name.lower():
            values = [m.cpu_percent for m in recent_metrics]
        elif "memory" in rule.name.lower():
            values = [m.memory_percent for m in recent_metrics]
        elif "disk" in rule.name.lower():
            values = [m.disk_usage_percent for m in recent_metrics]
        else:
            return False
        
        # Evaluate condition
        avg_value = sum(values) / len(values)
        
        if rule.condition == "gt":
            return avg_value > rule.threshold
        elif rule.condition == "lt":
            return avg_value < rule.threshold
        elif rule.condition == "eq":
            return abs(avg_value - rule.threshold) < 0.1
        
        return False
    
    def _evaluate_workflow_rule(self, rule: AlertRule) -> bool:
        """Evaluate workflow metric alert rule"""
        window_start = datetime.utcnow() - timedelta(minutes=rule.window_minutes)
        
        recent_workflows = [
            m for m in self.metrics_collector.workflow_metrics_history
            if datetime.fromisoformat(m.timestamp) > window_start
        ]
        
        if not recent_workflows:
            return False
        
        # Calculate failure rate
        if "failure_rate" in rule.name.lower():
            failed_count = sum(1 for w in recent_workflows if w.status == "failed")
            failure_rate = (failed_count / len(recent_workflows)) * 100
            
            if rule.condition == "gt":
                return failure_rate > rule.threshold
        
        # Calculate average duration
        elif "duration" in rule.name.lower():
            durations = [w.duration for w in recent_workflows]
            avg_duration = sum(durations) / len(durations)
            
            if rule.condition == "gt":
                return avg_duration > rule.threshold
        
        return False
    
    def _evaluate_error_rate_rule(self, rule: AlertRule) -> bool:
        """Evaluate error rate alert rule"""
        error_summary = error_monitor.get_error_summary(hours=rule.window_minutes / 60)
        
        if "total_errors" not in error_summary:
            return False
        
        error_count = error_summary["total_errors"]
        
        if rule.condition == "gt":
            return error_count > rule.threshold
        
        return False
    
    def _trigger_alert(self, rule: AlertRule, current_time: datetime):
        """Trigger an alert"""
        alert_data = {
            "rule_name": rule.name,
            "severity": rule.severity,
            "threshold": rule.threshold,
            "condition": rule.condition,
            "timestamp": current_time.isoformat(),
            "message": f"Alert triggered: {rule.name}"
        }
        
        # Record active alert
        self.active_alerts[rule.name] = {
            "timestamp": current_time,
            "data": alert_data
        }
        
        # Add to history
        self.alert_history.append(alert_data)
        
        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
        
        logger.warning(f"ALERT TRIGGERED: {rule.name} - {alert_data['message']}")
    
    def _clear_alert(self, rule_name: str, current_time: datetime):
        """Clear an active alert"""
        if rule_name in self.active_alerts:
            del self.active_alerts[rule_name]
            
            clear_data = {
                "rule_name": rule_name,
                "timestamp": current_time.isoformat(),
                "message": f"Alert cleared: {rule_name}"
            }
            
            self.alert_history.append(clear_data)
            logger.info(f"ALERT CLEARED: {rule_name}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of currently active alerts"""
        return [alert["data"] for alert in self.active_alerts.values()]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified time period"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


class MonitoringDashboard:
    """
    Provides monitoring dashboard data and health checks
    """
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        # Get recent metrics
        system_summary = self.metrics_collector.get_system_metrics_summary(hours=1)
        workflow_summary = self.metrics_collector.get_workflow_metrics_summary(hours=1)
        error_summary = error_monitor.get_error_summary(hours=1)
        performance_summary = performance_monitor.get_performance_summary(hours=1)
        
        # Determine overall health
        health_score = 100
        issues = []
        
        # Check system resources
        if "cpu" in system_summary and system_summary["cpu"]["avg"] > 80:
            health_score -= 20
            issues.append("High CPU usage")
        
        if "memory" in system_summary and system_summary["memory"]["avg"] > 85:
            health_score -= 20
            issues.append("High memory usage")
        
        # Check workflow success rate
        if "success_rate" in workflow_summary and workflow_summary["success_rate"] < 0.9:
            health_score -= 30
            issues.append("Low workflow success rate")
        
        # Check error rate
        if error_summary.get("total_errors", 0) > 10:
            health_score -= 20
            issues.append("High error rate")
        
        # Check active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a["severity"] == "critical"]
        if critical_alerts:
            health_score -= 40
            issues.append(f"{len(critical_alerts)} critical alerts")
        
        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "active_alerts": len(active_alerts),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "health": self.get_health_status(),
            "system_metrics": self.metrics_collector.get_system_metrics_summary(hours=1),
            "workflow_metrics": self.metrics_collector.get_workflow_metrics_summary(hours=1),
            "error_summary": error_monitor.get_error_summary(hours=1),
            "performance_summary": performance_monitor.get_performance_summary(hours=1),
            "active_alerts": self.alert_manager.get_active_alerts(),
            "resource_usage": resource_monitor.get_resource_summary()
        }


# Default alert rules
DEFAULT_ALERT_RULES = [
    AlertRule(
        name="high_cpu_usage",
        metric_type="system",
        condition="gt",
        threshold=80.0,
        window_minutes=5,
        severity="high"
    ),
    AlertRule(
        name="high_memory_usage",
        metric_type="system",
        condition="gt",
        threshold=85.0,
        window_minutes=5,
        severity="high"
    ),
    AlertRule(
        name="high_workflow_failure_rate",
        metric_type="workflow",
        condition="gt",
        threshold=20.0,  # 20% failure rate
        window_minutes=15,
        severity="critical"
    ),
    AlertRule(
        name="slow_workflow_performance",
        metric_type="workflow",
        condition="gt",
        threshold=300.0,  # 5 minutes average
        window_minutes=30,
        severity="medium"
    ),
    AlertRule(
        name="high_error_rate",
        metric_type="error_rate",
        condition="gt",
        threshold=10.0,  # 10 errors per hour
        window_minutes=60,
        severity="high"
    )
]


# Global monitoring instances
_metrics_collector: Optional[MetricsCollector] = None
_alert_manager: Optional[AlertManager] = None
_monitoring_dashboard: Optional[MonitoringDashboard] = None


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector singleton"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        _metrics_collector.start_collection()
    return _metrics_collector


def get_alert_manager() -> AlertManager:
    """Get alert manager singleton"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(get_metrics_collector())
        
        # Add default alert rules
        for rule in DEFAULT_ALERT_RULES:
            _alert_manager.add_alert_rule(rule)
        
        # Add default notification handler (logging)
        _alert_manager.add_notification_handler(
            lambda alert: logger.critical(f"ALERT: {alert['rule_name']} - {alert['message']}")
        )
    
    return _alert_manager


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get monitoring dashboard singleton"""
    global _monitoring_dashboard
    if _monitoring_dashboard is None:
        _monitoring_dashboard = MonitoringDashboard(
            get_metrics_collector(),
            get_alert_manager()
        )
    return _monitoring_dashboard


# Background task to check alerts periodically
async def start_alert_monitoring():
    """Start background alert monitoring"""
    alert_manager = get_alert_manager()
    
    while True:
        try:
            alert_manager.check_alerts()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")
            await asyncio.sleep(60)