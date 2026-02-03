"""
Startup utilities for Data Analysis Agent

Handles initialization of monitoring, error handling, and background tasks
when the analysis agent starts up.
"""

import asyncio
import logging
from typing import Optional

from .monitoring import get_metrics_collector, get_alert_manager, start_alert_monitoring
from .error_handling import error_monitor


logger = logging.getLogger(__name__)


async def initialize_monitoring_system():
    """
    Initialize the complete monitoring system including metrics collection,
    alert management, and background monitoring tasks.
    """
    try:
        logger.info("Initializing Data Analysis Agent monitoring system...")
        
        # Initialize metrics collector
        metrics_collector = get_metrics_collector()
        if not metrics_collector.is_collecting:
            metrics_collector.start_collection()
            logger.info("Started metrics collection")
        
        # Initialize alert manager with default rules
        alert_manager = get_alert_manager()
        logger.info(f"Initialized alert manager with {len(alert_manager.alert_rules)} rules")
        
        # Start background alert monitoring
        asyncio.create_task(start_alert_monitoring())
        logger.info("Started background alert monitoring")
        
        # Log successful initialization
        logger.info("Data Analysis Agent monitoring system initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        return False


async def shutdown_monitoring_system():
    """
    Gracefully shutdown the monitoring system
    """
    try:
        logger.info("Shutting down Data Analysis Agent monitoring system...")
        
        # Stop metrics collection
        metrics_collector = get_metrics_collector()
        if metrics_collector.is_collecting:
            metrics_collector.stop_collection()
            logger.info("Stopped metrics collection")
        
        logger.info("Data Analysis Agent monitoring system shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during monitoring system shutdown: {e}")


def setup_logging():
    """
    Setup enhanced logging configuration for the analysis agent
    """
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("data_analysis_agent.log", mode="a")
        ]
    )
    
    # Set specific log levels for different components
    logging.getLogger("market_research").setLevel(logging.INFO)
    logging.getLogger("market_research.monitoring").setLevel(logging.INFO)
    logging.getLogger("market_research.error_handling").setLevel(logging.WARNING)
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger.info("Enhanced logging configuration applied")


# Startup function to be called when the service starts
async def startup_data_analysis_agent():
    """
    Main startup function for the Data Analysis Agent
    
    This should be called when the FastAPI application starts up
    """
    try:
        # Setup logging
        setup_logging()
        
        # Initialize monitoring system
        monitoring_success = await initialize_monitoring_system()
        
        if monitoring_success:
            logger.info("Data Analysis Agent startup completed successfully")
        else:
            logger.warning("Data Analysis Agent started with monitoring issues")
        
        return monitoring_success
        
    except Exception as e:
        logger.error(f"Critical error during Data Analysis Agent startup: {e}")
        raise


# Shutdown function to be called when the service stops
async def shutdown_data_analysis_agent():
    """
    Main shutdown function for the Data Analysis Agent
    
    This should be called when the FastAPI application shuts down
    """
    try:
        await shutdown_monitoring_system()
        logger.info("Data Analysis Agent shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during Data Analysis Agent shutdown: {e}")


# Health check function
def get_agent_health_status() -> dict:
    """
    Get basic health status of the analysis agent
    
    Returns:
        Dictionary with health status information
    """
    try:
        from .monitoring import get_monitoring_dashboard
        
        dashboard = get_monitoring_dashboard()
        health_data = dashboard.get_health_status()
        
        return {
            "service": "data_analysis_agent",
            "status": health_data["status"],
            "health_score": health_data["health_score"],
            "monitoring_active": True,
            "timestamp": health_data["timestamp"]
        }
        
    except Exception as e:
        return {
            "service": "data_analysis_agent",
            "status": "error",
            "health_score": 0,
            "monitoring_active": False,
            "error": str(e),
            "timestamp": None
        }