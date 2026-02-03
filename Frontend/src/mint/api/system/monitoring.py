"""
System metrics service for admin dashboard.

This service provides comprehensive system monitoring capabilities including
infrastructure metrics, agent status tracking, and API health monitoring.
"""

import logging
import asyncio
import psutil
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import aiohttp
from .core.supabase_client import get_supabase_client
from ..cache import cached
from ...schemas.schemas import (
    SystemMetric,
    SystemMetricCreate,
    MetricType,
    AgentStatusRecord,
    AgentStatusUpdate,
    AgentStatus,
    APIHealthRecord,
    APIHealthCheck,
    MetricsQuery,
    MetricsAggregated,
    AgentStatusSummary,
    APIHealthSummary
)

logger = logging.getLogger(__name__)


class SystemMetricsService:
    """Service for managing system metrics and monitoring."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self._monitoring_active = False
    
    async def record_metric(
        self,
        metric_type: MetricType,
        metric_name: str,
        value: float,
        unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> str:
        """
        Record a system metric.
        
        Args:
            metric_type: Category of the metric
            metric_name: Specific metric name
            value: Metric value
            unit: Unit of measurement
            tags: Additional metadata
            source: Source system or component
            
        Returns:
            ID of the created metric record
        """
        try:
            result = self.supabase.rpc(
                'record_system_metric',
                {
                    'p_metric_type': metric_type.value,
                    'p_metric_name': metric_name,
                    'p_value': value,
                    'p_unit': unit,
                    'p_tags': tags or {},
                    'p_source': source
                }
            ).execute()
            
            if result.data:
                metric_id = result.data
                logger.debug(f"Recorded metric: {metric_type.value}.{metric_name} = {value}")
                return metric_id
            else:
                logger.error("Failed to record metric - no data returned")
                raise Exception("Failed to record metric")
                
        except Exception as e:
            logger.error(f"Error recording metric: {str(e)}")
            raise
    
    async def update_agent_status(self, update: AgentStatusUpdate) -> bool:
        """
        Update agent status and performance metrics.
        
        Args:
            update: Agent status update data
            
        Returns:
            True if update was successful
        """
        try:
            result = self.supabase.rpc(
                'update_agent_status',
                {
                    'p_agent_name': update.agent_name,
                    'p_status': update.status.value if update.status else None,
                    'p_execution_time': update.execution_time,
                    'p_success': update.success,
                    'p_job_id': update.job_id,
                    'p_error_message': update.error_message,
                    'p_performance_metrics': update.performance_metrics
                }
            ).execute()
            
            if result.data:
                logger.debug(f"Updated agent status: {update.agent_name}")
                return True
            else:
                logger.error(f"Failed to update agent status: {update.agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent status: {str(e)}")
            raise
    
    async def record_api_health(self, health_check: APIHealthCheck) -> str:
        """
        Record an API health check result.
        
        Args:
            health_check: API health check data
            
        Returns:
            ID of the created health record
        """
        try:
            result = self.supabase.rpc(
                'record_api_health',
                {
                    'p_api_name': health_check.api_name,
                    'p_endpoint': health_check.endpoint,
                    'p_status_code': health_check.status_code,
                    'p_response_time': health_check.response_time,
                    'p_success': health_check.success,
                    'p_error_message': health_check.error_message
                }
            ).execute()
            
            if result.data:
                health_id = result.data
                logger.debug(f"Recorded API health: {health_check.api_name} - {health_check.success}")
                return health_id
            else:
                logger.error("Failed to record API health - no data returned")
                raise Exception("Failed to record API health")
                
        except Exception as e:
            logger.error(f"Error recording API health: {str(e)}")
            raise
    
    @cached(ttl_seconds=300, key_prefix="metrics", tags=["metrics", "admin_dashboard"])
    async def get_metrics_aggregated(self, query: MetricsQuery) -> List[MetricsAggregated]:
        """
        Get aggregated metrics data.
        
        Args:
            query: Query parameters for filtering and aggregation
            
        Returns:
            List of aggregated metrics
        """
        try:
            # Determine appropriate TTL based on query time range
            # Recent data changes more frequently, so cache for less time
            cache_ttl = 300  # Default 5 minutes
            
            if query.start_date and query.end_date:
                time_range = (query.end_date - query.start_date).total_seconds()
                # For historical data (more than 1 day), cache longer
                if time_range > 86400:  # 24 hours in seconds
                    cache_ttl = 1800  # 30 minutes
                # For very recent data (less than 1 hour), cache for less time
                elif time_range < 3600:  # 1 hour in seconds
                    cache_ttl = 60  # 1 minute
            
            result = self.supabase.rpc(
                'get_system_metrics_aggregated',
                {
                    'p_metric_type': query.metric_type.value if query.metric_type else None,
                    'p_metric_name': query.metric_name,
                    'p_start_date': query.start_date.isoformat() if query.start_date else None,
                    'p_end_date': query.end_date.isoformat() if query.end_date else None,
                    'p_interval': query.interval
                }
            ).execute()
            
            metrics = []
            if result.data:
                for row in result.data:
                    metric = MetricsAggregated(
                        time_bucket=datetime.fromisoformat(row['time_bucket'].replace('Z', '+00:00')),
                        metric_type=row['metric_type'],
                        metric_name=row['metric_name'],
                        avg_value=float(row['avg_value']),
                        min_value=float(row['min_value']),
                        max_value=float(row['max_value']),
                        count_values=int(row['count_values'])
                    )
                    metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving aggregated metrics: {str(e)}")
            raise
    
    @cached(ttl_seconds=60, key_prefix="agent", tags=["agent_status", "admin_dashboard"])
    async def get_agent_status_summary(self) -> AgentStatusSummary:
        """
        Get summary of all agent statuses.
        
        Returns:
            Summary of agent statuses
        """
        try:
            result = self.supabase.rpc('get_agent_status_summary').execute()
            
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return AgentStatusSummary(
                    total_agents=row['total_agents'],
                    active_agents=row['active_agents'],
                    idle_agents=row['idle_agents'],
                    error_agents=row['error_agents'],
                    avg_success_rate=float(row['avg_success_rate'] or 0),
                    avg_execution_time=float(row['avg_execution_time'] or 0)
                )
            else:
                return AgentStatusSummary(
                    total_agents=0,
                    active_agents=0,
                    idle_agents=0,
                    error_agents=0,
                    avg_success_rate=0.0,
                    avg_execution_time=0.0
                )
                
        except Exception as e:
            logger.error(f"Error retrieving agent status summary: {str(e)}")
            raise
    
    @cached(ttl_seconds=300, key_prefix="api_health", tags=["api_health", "admin_dashboard"])
    async def get_api_health_summary(self, hours_back: int = 24) -> List[APIHealthSummary]:
        """
        Get summary of API health statuses.
        
        Args:
            hours_back: Number of hours to look back for health data
            
        Returns:
            List of API health summaries
        """
        try:
            result = self.supabase.rpc(
                'get_api_health_summary',
                {'p_hours_back': hours_back}
            ).execute()
            
            summaries = []
            if result.data:
                for row in result.data:
                    summary = APIHealthSummary(
                        api_name=row['api_name'],
                        total_checks=row['total_checks'],
                        successful_checks=row['successful_checks'],
                        failed_checks=row['failed_checks'],
                        success_rate=float(row['success_rate']),
                        avg_response_time=float(row['avg_response_time']) if row['avg_response_time'] else None,
                        last_check=datetime.fromisoformat(row['last_check'].replace('Z', '+00:00')) if row['last_check'] else None,
                        last_success=datetime.fromisoformat(row['last_success'].replace('Z', '+00:00')) if row['last_success'] else None,
                        current_status=row['current_status']
                    )
                    summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error retrieving API health summary: {str(e)}")
            raise
    
    async def get_agent_statuses(self) -> List[AgentStatusRecord]:
        """
        Get detailed status for all agents.
        
        Returns:
            List of agent status records
        """
        try:
            result = self.supabase.table('agent_status').select('*').execute()
            
            statuses = []
            if result.data:
                for row in result.data:
                    status = AgentStatusRecord(
                        id=row['id'],
                        agent_name=row['agent_name'],
                        status=AgentStatus(row['status']),
                        last_execution=datetime.fromisoformat(row['last_execution'].replace('Z', '+00:00')) if row['last_execution'] else None,
                        last_success=datetime.fromisoformat(row['last_success'].replace('Z', '+00:00')) if row['last_success'] else None,
                        last_error=datetime.fromisoformat(row['last_error'].replace('Z', '+00:00')) if row['last_error'] else None,
                        success_rate=float(row['success_rate']),
                        average_execution_time=float(row['average_execution_time']),
                        total_executions=row['total_executions'],
                        successful_executions=row['successful_executions'],
                        failed_executions=row['failed_executions'],
                        current_job_id=row['current_job_id'],
                        error_message=row['error_message'],
                        performance_metrics=row['performance_metrics'] or {},
                        health_check_at=datetime.fromisoformat(row['health_check_at'].replace('Z', '+00:00')),
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                    )
                    statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"Error retrieving agent statuses: {str(e)}")
            raise
    
    # Infrastructure monitoring methods
    
    async def collect_infrastructure_metrics(self):
        """Collect and record infrastructure metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric(
                MetricType.INFRASTRUCTURE,
                'cpu_usage',
                cpu_percent,
                'percent',
                source='system'
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self.record_metric(
                MetricType.INFRASTRUCTURE,
                'memory_usage',
                memory.percent,
                'percent',
                {'total': memory.total, 'available': memory.available},
                'system'
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            await self.record_metric(
                MetricType.INFRASTRUCTURE,
                'disk_usage',
                disk_percent,
                'percent',
                {'total': disk.total, 'used': disk.used, 'free': disk.free},
                'system'
            )
            
            # Network I/O
            network = psutil.net_io_counters()
            await self.record_metric(
                MetricType.INFRASTRUCTURE,
                'network_bytes_sent',
                network.bytes_sent,
                'bytes',
                source='system'
            )
            await self.record_metric(
                MetricType.INFRASTRUCTURE,
                'network_bytes_recv',
                network.bytes_recv,
                'bytes',
                source='system'
            )
            
        except Exception as e:
            logger.error(f"Error collecting infrastructure metrics: {str(e)}")
    
    async def check_api_health(self, api_configs: List[Dict[str, str]]):
        """
        Check health of external APIs.
        
        Args:
            api_configs: List of API configurations with 'name' and 'url' keys
        """
        async with aiohttp.ClientSession() as session:
            for config in api_configs:
                try:
                    start_time = time.time()
                    async with session.get(
                        config['url'],
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                        
                        await self.record_api_health(APIHealthCheck(
                            api_name=config['name'],
                            endpoint=config['url'],
                            status_code=response.status,
                            response_time=response_time,
                            success=200 <= response.status < 400
                        ))
                        
                except asyncio.TimeoutError:
                    await self.record_api_health(APIHealthCheck(
                        api_name=config['name'],
                        endpoint=config['url'],
                        success=False,
                        error_message="Request timeout"
                    ))
                except Exception as e:
                    await self.record_api_health(APIHealthCheck(
                        api_name=config['name'],
                        endpoint=config['url'],
                        success=False,
                        error_message=str(e)
                    ))
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """
        Start continuous system monitoring.
        
        Args:
            interval_seconds: Interval between monitoring cycles
        """
        self._monitoring_active = True
        logger.info("Starting system monitoring")
        
        # Example API configurations - these should come from config
        api_configs = [
            {'name': 'openai', 'url': 'https://api.openai.com/v1/models'},
            {'name': 'serper', 'url': 'https://google.serper.dev/search'},
        ]
        
        while self._monitoring_active:
            try:
                # Collect infrastructure metrics
                await self.collect_infrastructure_metrics()
                
                # Check API health
                await self.check_api_health(api_configs)
                
                # Wait for next cycle
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {str(e)}")
                await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Stop continuous system monitoring."""
        self._monitoring_active = False
        logger.info("Stopping system monitoring")


# Global metrics service instance
metrics_service = SystemMetricsService()