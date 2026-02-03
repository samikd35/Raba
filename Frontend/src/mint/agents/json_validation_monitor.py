"""
JSON Validation Monitoring Module

This module provides monitoring capabilities for the JSON validation system,
tracking success rates, performance metrics, and error patterns.
"""

import os
import json
import time
import logging
import threading
from collections import Counter, deque
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Setup logging
logger = logging.getLogger("json_validation_monitor")

class JSONValidationMonitor:
    """
    Monitor for the JSON validation system that tracks success rates,
    performance metrics, and error patterns.
    """
    
    def __init__(self, config_path: str = "monitoring/json_validation_monitoring.json"):
        """
        Initialize the JSON validation monitor.
        
        Args:
            config_path: Path to the monitoring configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize metrics storage
        self.validation_results = deque(maxlen=self.config["metrics"]["success_rate"]["window_size"])
        self.performance_metrics = deque(maxlen=1000)  # Store last 1000 performance measurements
        self.error_patterns = Counter()
        
        # Initialize lock for thread safety
        self.lock = threading.Lock()
        
        # Start periodic metrics reporting if enabled
        if self.config["settings"]["enabled"]:
            self._start_periodic_reporting()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration from file."""
        try:
            config_path = os.path.join("Backend", self.config_path)
            if not os.path.exists(config_path):
                logger.warning(f"Monitoring config file {config_path} not found, using default config")
                return self._default_config()
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load monitoring configuration: {str(e)}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default monitoring configuration."""
        return {
            "timestamp": datetime.now().isoformat(),
            "settings": {
                "enabled": True,
                "log_level": "INFO",
                "metrics_interval": 300,  # 5 minutes
                "alert_threshold": 0.001,  # 99.9% success rate
                "notification_email": "admin@example.com"
            },
            "metrics": {
                "success_rate": {
                    "enabled": True,
                    "threshold": 0.001,  # 99.9% success rate
                    "window_size": 100  # Last 100 validations
                },
                "performance": {
                    "enabled": True,
                    "sample_rate": 0.1,  # 10% of requests
                    "slow_threshold_ms": 1000  # 1 second
                },
                "error_patterns": {
                    "enabled": True,
                    "top_patterns": 10,
                    "min_occurrences": 3
                }
            }
        }
    
    def _start_periodic_reporting(self):
        """Start periodic reporting of metrics."""
        def report_metrics():
            while True:
                time.sleep(self.config["settings"]["metrics_interval"])
                self.report_metrics()
        
        thread = threading.Thread(target=report_metrics, daemon=True)
        thread.start()
    
    def record_validation_result(self, success: bool, error_type: Optional[str] = None, 
                                 duration_ms: Optional[float] = None) -> None:
        """
        Record a validation result.
        
        Args:
            success: Whether the validation was successful
            error_type: Type of error if validation failed
            duration_ms: Duration of validation in milliseconds
        """
        with self.lock:
            # Record success/failure
            self.validation_results.append(success)
            
            # Record error pattern if validation failed
            if not success and error_type:
                self.error_patterns[error_type] += 1
            
            # Record performance metric if provided and sampling passes
            if duration_ms is not None and self.config["metrics"]["performance"]["enabled"]:
                if self.config["metrics"]["performance"]["sample_rate"] >= 1.0 or \
                   random.random() < self.config["metrics"]["performance"]["sample_rate"]:
                    self.performance_metrics.append(duration_ms)
                    
                    # Log slow validations
                    if duration_ms > self.config["metrics"]["performance"]["slow_threshold_ms"]:
                        logger.warning(f"Slow validation detected: {duration_ms:.2f}ms")
            
            # Check if success rate is below threshold
            success_rate = self.get_success_rate()
            if success_rate < (1 - self.config["metrics"]["success_rate"]["threshold"]):
                logger.warning(f"Success rate ({success_rate:.4f}) below threshold "
                              f"({1 - self.config['metrics']['success_rate']['threshold']:.4f})")
                self._send_alert(success_rate)
    
    def get_success_rate(self) -> float:
        """Get the current success rate."""
        with self.lock:
            if not self.validation_results:
                return 1.0  # No data yet, assume perfect
            return sum(self.validation_results) / len(self.validation_results)
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        with self.lock:
            if not self.performance_metrics:
                return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "max_ms": 0}
            
            metrics_list = list(self.performance_metrics)
            metrics_list.sort()
            
            return {
                "avg_ms": sum(metrics_list) / len(metrics_list),
                "p50_ms": metrics_list[len(metrics_list) // 2],
                "p95_ms": metrics_list[int(len(metrics_list) * 0.95)],
                "p99_ms": metrics_list[int(len(metrics_list) * 0.99)],
                "max_ms": max(metrics_list)
            }
    
    def get_top_error_patterns(self, n: int = None) -> List[Tuple[str, int]]:
        """
        Get the top N error patterns.
        
        Args:
            n: Number of top error patterns to return, defaults to config value
        
        Returns:
            List of (error_pattern, count) tuples
        """
        if n is None:
            n = self.config["metrics"]["error_patterns"]["top_patterns"]
        
        with self.lock:
            min_occurrences = self.config["metrics"]["error_patterns"]["min_occurrences"]
            return [(pattern, count) for pattern, count in self.error_patterns.most_common(n) 
                    if count >= min_occurrences]
    
    def report_metrics(self) -> Dict[str, Any]:
        """
        Generate and report current metrics.
        
        Returns:
            Dictionary of metrics
        """
        success_rate = self.get_success_rate()
        performance_stats = self.get_performance_stats()
        top_errors = self.get_top_error_patterns()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "success_rate": success_rate,
            "performance": performance_stats,
            "top_errors": [{"pattern": p, "count": c} for p, c in top_errors],
            "total_validations": len(self.validation_results),
            "total_errors": sum(1 for r in self.validation_results if not r)
        }
        
        # Log metrics
        logger.info(f"JSON Validation Metrics: "
                   f"Success Rate: {success_rate:.4f}, "
                   f"Avg Duration: {performance_stats['avg_ms']:.2f}ms, "
                   f"P95 Duration: {performance_stats['p95_ms']:.2f}ms")
        
        if top_errors:
            logger.info(f"Top Error Patterns: {', '.join([f'{p} ({c})' for p, c in top_errors[:3]])}")
        
        # Save metrics to file
        self._save_metrics(metrics)
        
        return metrics
    
    def _save_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save metrics to file."""
        try:
            os.makedirs(os.path.join("Backend", "monitoring", "metrics"), exist_ok=True)
            filename = f"json_validation_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join("Backend", "monitoring", "metrics", filename)
            
            with open(filepath, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Also update latest metrics file
            latest_filepath = os.path.join("Backend", "monitoring", "json_validation_latest_metrics.json")
            with open(latest_filepath, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
    
    def _send_alert(self, current_rate: float) -> None:
        """
        Send an alert when success rate falls below threshold.
        
        Args:
            current_rate: Current success rate
        """
        threshold = 1 - self.config["metrics"]["success_rate"]["threshold"]
        logger.error(f"ALERT: JSON validation success rate ({current_rate:.4f}) "
                    f"below threshold ({threshold:.4f})")
        
        # In a real implementation, this would send an email or notification
        # For now, we just log the alert
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": "success_rate_alert",
            "current_rate": current_rate,
            "threshold": threshold,
            "top_errors": self.get_top_error_patterns(5)
        }
        
        try:
            os.makedirs(os.path.join("Backend", "monitoring", "alerts"), exist_ok=True)
            filename = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join("Backend", "monitoring", "alerts", filename)
            
            with open(filepath, 'w') as f:
                json.dump(alert, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alert: {str(e)}")

# Singleton instance
_monitor_instance = None

def get_monitor() -> JSONValidationMonitor:
    """Get the singleton monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = JSONValidationMonitor()
    return _monitor_instance

# Import this at the end to avoid circular imports
import random