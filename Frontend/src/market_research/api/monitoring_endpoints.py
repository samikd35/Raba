"""
Monitoring API Endpoints for Data Analysis Agent

Provides REST endpoints for accessing monitoring data, health status,
and system metrics for the analysis workflows.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from src.mint.api.auth_v2.utils import get_current_user

from ..adapters.auth_adapter import AnalysisAgentAuthAdapter
from ..utils.error_handling import (error_monitor, performance_monitor,
                                    resource_monitor)
from ..utils.monitoring import (get_alert_manager, get_metrics_collector,
                                get_monitoring_dashboard)

logger = logging.getLogger(__name__)

# Create router for monitoring endpoints
monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])

logger.info("🔍 MONITORING DEBUG: Monitoring router created")
logger.info(f"🔍 MONITORING DEBUG: Router prefix: {monitoring_router.prefix}")
logger.info(f"🔍 MONITORING DEBUG: Router tags: {monitoring_router.tags}")


async def get_auth_adapter():
    """Dependency to get auth adapter"""
    return AnalysisAgentAuthAdapter()


@monitoring_router.get("/health")
async def get_health_status():
    """
    Get overall system health status

    Returns:
        Health status with score and issues
    """
    try:
        dashboard = get_monitoring_dashboard()
        health_data = dashboard.get_health_status()

        return JSONResponse(
            status_code=200 if health_data["status"] in ["healthy", "warning"] else 503,
            content={"success": True, "data": health_data},
        )
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to get health status",
                "message": str(e),
            },
        )


@monitoring_router.get("/dashboard")
async def get_dashboard_data(
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get comprehensive monitoring dashboard data

    Requires authentication for detailed system information
    """
    try:
        dashboard = get_monitoring_dashboard()
        dashboard_data = dashboard.get_dashboard_data()

        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get dashboard data", "message": str(e)},
        )


@monitoring_router.get("/metrics/system")
async def get_system_metrics(
    hours: int = Query(1, ge=1, le=24, description="Hours of metrics to retrieve"),
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get system resource metrics for specified time period

    Args:
        hours: Number of hours of metrics to retrieve (1-24)
    """
    try:
        metrics_collector = get_metrics_collector()
        system_metrics = metrics_collector.get_system_metrics_summary(hours=hours)

        return {
            "success": True,
            "data": system_metrics,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get system metrics", "message": str(e)},
        )


@monitoring_router.get("/metrics/workflows")
async def get_workflow_metrics(
    hours: int = Query(1, ge=1, le=24, description="Hours of metrics to retrieve"),
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get workflow execution metrics for specified time period

    Args:
        hours: Number of hours of metrics to retrieve (1-24)
    """
    try:
        metrics_collector = get_metrics_collector()
        workflow_metrics = metrics_collector.get_workflow_metrics_summary(hours=hours)

        return {
            "success": True,
            "data": workflow_metrics,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting workflow metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get workflow metrics", "message": str(e)},
        )


@monitoring_router.get("/metrics/performance")
async def get_performance_metrics(
    hours: int = Query(1, ge=1, le=24, description="Hours of metrics to retrieve"),
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get performance metrics for specified time period

    Args:
        hours: Number of hours of metrics to retrieve (1-24)
    """
    try:
        performance_summary = performance_monitor.get_performance_summary(hours=hours)

        return {
            "success": True,
            "data": performance_summary,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get performance metrics", "message": str(e)},
        )


@monitoring_router.get("/errors")
async def get_error_summary(
    hours: int = Query(1, ge=1, le=24, description="Hours of errors to retrieve"),
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get error summary for specified time period

    Args:
        hours: Number of hours of errors to retrieve (1-24)
    """
    try:
        error_summary = error_monitor.get_error_summary(hours=hours)

        return {
            "success": True,
            "data": error_summary,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get error summary", "message": str(e)},
        )


@monitoring_router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Return only active alerts"),
    hours: int = Query(
        24, ge=1, le=168, description="Hours of alert history to retrieve"
    ),
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get alert information

    Args:
        active_only: If True, return only currently active alerts
        hours: Number of hours of alert history to retrieve (1-168)
    """
    try:
        alert_manager = get_alert_manager()

        if active_only:
            alerts_data = alert_manager.get_active_alerts()
        else:
            alerts_data = alert_manager.get_alert_history(hours=hours)

        return {
            "success": True,
            "data": {
                "alerts": alerts_data,
                "active_count": len(alert_manager.get_active_alerts()),
                "total_count": len(alerts_data),
            },
            "active_only": active_only,
            "period_hours": hours if not active_only else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(
            status_code=500, detail={"error": "Failed to get alerts", "message": str(e)}
        )


@monitoring_router.get("/resources")
async def get_resource_usage(
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get current resource usage information
    """
    try:
        resource_summary = resource_monitor.get_resource_summary()

        return {
            "success": True,
            "data": resource_summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting resource usage: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get resource usage", "message": str(e)},
        )


@monitoring_router.post("/alerts/test")
async def trigger_test_alert(
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger a test alert for monitoring system validation
    """
    try:
        alert_manager = get_alert_manager()

        # Create a test alert
        test_alert = {
            "rule_name": "test_alert",
            "severity": "low",
            "threshold": 0,
            "condition": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test alert triggered manually",
        }

        # Add to alert history
        alert_manager.alert_history.append(test_alert)

        logger.info("Test alert triggered manually")

        return {
            "success": True,
            "message": "Test alert triggered successfully",
            "alert": test_alert,
        }
    except Exception as e:
        logger.error(f"Error triggering test alert: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to trigger test alert", "message": str(e)},
        )


@monitoring_router.get("/status/detailed")
async def get_detailed_status(
    auth_adapter: AnalysisAgentAuthAdapter = Depends(get_auth_adapter),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed system status including all monitoring components
    """
    try:
        dashboard = get_monitoring_dashboard()
        metrics_collector = get_metrics_collector()
        alert_manager = get_alert_manager()

        # Get AI service status if available
        ai_service_status = {}
        try:
            from ..utils.ai_service_wrapper import get_ai_service_wrapper

            ai_wrapper = get_ai_service_wrapper()
            ai_service_status = ai_wrapper.get_service_status()
        except Exception as e:
            ai_service_status = {"error": f"Failed to get AI service status: {e}"}

        detailed_status = {
            "overall_health": dashboard.get_health_status(),
            "system_metrics": metrics_collector.get_system_metrics_summary(hours=1),
            "workflow_metrics": metrics_collector.get_workflow_metrics_summary(hours=1),
            "error_summary": error_monitor.get_error_summary(hours=1),
            "performance_summary": performance_monitor.get_performance_summary(hours=1),
            "resource_usage": resource_monitor.get_resource_summary(),
            "active_alerts": alert_manager.get_active_alerts(),
            "ai_service_status": ai_service_status,
            "monitoring_components": {
                "metrics_collector_active": metrics_collector.is_collecting,
                "alert_rules_count": len(alert_manager.alert_rules),
                "notification_handlers_count": len(alert_manager.notification_handlers),
            },
        }

        return {
            "success": True,
            "data": detailed_status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting detailed status: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get detailed status", "message": str(e)},
        )


# ---------- Monitoring Router Debug Information ----------
logger.info("🔍 MONITORING DEBUG: Monitoring router setup complete")
logger.info(f"🔍 MONITORING DEBUG: Final monitoring router has {len(monitoring_router.routes)} routes")

# Log all registered monitoring routes for debugging
for i, route in enumerate(monitoring_router.routes):
    route_info = {
        'path': getattr(route, 'path', 'unknown'),
        'methods': getattr(route, 'methods', 'unknown'),
        'name': getattr(route, 'name', 'unknown')
    }
    logger.info(f"🔍 MONITORING DEBUG: Route {i+1}: {route_info['methods']} {route_info['path']} (name: {route_info['name']})")

logger.info("🔍 MONITORING DEBUG: Monitoring router ready for inclusion")

