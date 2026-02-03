"""
Celery worker for processing MINT research jobs.

This module defines tasks for running research workflows in the background
using Celery, with Redis as the message broker.
"""

import os
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import json

from celery import Celery, Task
from celery.exceptions import MaxRetriesExceededError
from dotenv import load_dotenv

from src.mint.schemas.schemas import JobStatus
from src.mint.api.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from src.mint.workflow import execute_workflow, CheckpointManager

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Celery configuration
# Use Redis Cloud in Azure as the default connection for production
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-19601.c251.east-us-mz.azure.redns.redis-cloud.com')
REDIS_PORT = os.getenv('REDIS_PORT', '19601')
REDIS_USERNAME = os.getenv('REDIS_USERNAME', 'default')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '6rxWI1Q0CU4JT4wRNWZrRUEyA6kYfBWQ')

# Construct Redis URL with credentials
REDIS_URL = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# Set Celery broker and backend to the Redis URL
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

# Create Celery app
celery_app = Celery(
    "mint_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    broker_connection_retry_on_startup=True,
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result configuration
    task_ignore_result=False,
    result_expires=60 * 60 * 24 * 7,  # 7 days
)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_client = get_service_role_client()


class BaseJobTask(Task):
    """Base task for MINT jobs with common error handling."""
    
    max_retries = 2
    default_retry_delay = 30  # 30 seconds
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure by updating job status.
        
        Args:
            exc: The exception that caused the failure
            task_id: The Celery task ID
            args: The task arguments
            kwargs: The task keyword arguments
            einfo: The exception info
        """
        # Extract job_id from args
        if not args:
            logger.error(f"Task {task_id} failed with no job_id: {exc}")
            return
            
        job_id = args[0]
        user_id = args[1] if len(args) > 1 else None
        
        if not job_id or not user_id:
            logger.error(f"Task {task_id} failed with invalid arguments: {args}")
            return
        
        # Update job status to FAILED
        try:
            error_details = {
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "task_id": task_id,
            }
            
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.FAILED,
                result={"error_details": error_details}
            )
            
            logger.error(f"Job {job_id} failed: {exc}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status: {e}")


@celery_app.task(base=BaseJobTask, name="mint.process_job")
def process_job_task(job_id: str, user_id: str):
    """
    Process a research job.
    
    Args:
        job_id: The ID of the job to process
        user_id: The ID of the user who owns the job
    """
    logger.info(f"Processing job {job_id} for user {user_id}")
    
    try:
        # Get job details from Supabase
        job = supabase_client.get_job(job_id, user_id)
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"status": "error", "message": "Job not found"}
        
        # Update job status to PROCESSING
        supabase_client.update_job_status(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.PROCESSING
        )
        
        # Initialize the checkpoint manager
        checkpoint_manager = CheckpointManager(job_id)
        
        # Check if we have a saved state
        graph_state = checkpoint_manager.load()
        
        if not graph_state:
            # Create initial state - workflow expects session_id and initial_query
            graph_state = {
                "session_id": job_id,  # workflow expects session_id, not job_id
                "user_id": user_id,
                "initial_query": job.get("query"),  # workflow expects initial_query, not query
                "clarification_answers": job.get("clarification_answers"),
                "metadata": job.get("metadata", {})
            }
        
        # Run the workflow
        result = execute_workflow(graph_state, checkpoint_manager)
        
        if result.get("status") == "paused":
            # Workflow is paused waiting for clarification
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.AWAITING_USER_INPUT,
                result={
                    "clarification_questions": result.get("clarification_questions"),
                    "state": "paused"
                }
            )
            
            logger.info(f"Job {job_id} paused waiting for clarification")
            return {"status": "paused", "job_id": job_id}
            
        elif result.get("status") == "completed":
            # Workflow completed successfully
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.COMPLETED,
                result={
                    "final_report_uri": result.get("final_report_uri"),
                    "state": "completed"
                }
            )
            
            logger.info(f"Job {job_id} completed successfully")
            return {"status": "completed", "job_id": job_id}
            
        else:
            # Unexpected result
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.FAILED,
                result={
                    "error_details": {
                        "message": "Unexpected workflow result",
                        "result": result
                    }
                }
            )
            
            logger.error(f"Job {job_id} failed with unexpected result: {result}")
            return {"status": "error", "message": "Unexpected workflow result"}
            
    except Exception as e:
        logger.exception(f"Error processing job {job_id}: {e}")
        # Task will be retried or marked as failed by BaseJobTask.on_failure
        raise


@celery_app.task(base=BaseJobTask, name="mint.resume_workflow")
def resume_workflow_task(job_id: str, user_id: str):
    """
    Resume a paused workflow after receiving clarification answers.
    
    Args:
        job_id: The ID of the job to resume
        user_id: The ID of the user who owns the job
    """
    logger.info(f"Resuming job {job_id} for user {user_id}")
    
    try:
        # Get job details from Supabase
        job = supabase_client.get_job(job_id, user_id)
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"status": "error", "message": "Job not found"}
        
        # Update job status to PROCESSING
        supabase_client.update_job_status(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.PROCESSING
        )
        
        # Initialize the checkpoint manager
        checkpoint_manager = CheckpointManager(job_id)
        
        # Load the saved state
        graph_state = checkpoint_manager.load()
        
        if not graph_state:
            logger.error(f"No saved state found for job {job_id}")
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.FAILED,
                result={
                    "error_details": {
                        "message": "No saved state found"
                    }
                }
            )
            return {"status": "error", "message": "No saved state found"}
        
        # Update the state with clarification answers
        graph_state["clarification_answers"] = job.get("clarification_answers")
        
        # Run the workflow
        result = execute_workflow(graph_state, checkpoint_manager)
        
        if result.get("status") == "paused":
            # Workflow is paused waiting for more clarification
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.AWAITING_USER_INPUT,
                result={
                    "clarification_questions": result.get("clarification_questions"),
                    "state": "paused"
                }
            )
            
            logger.info(f"Job {job_id} paused waiting for clarification")
            return {"status": "paused", "job_id": job_id}
            
        elif result.get("status") == "completed":
            # Workflow completed successfully
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.COMPLETED,
                result={
                    "final_report_uri": result.get("final_report_uri"),
                    "state": "completed"
                }
            )
            
            logger.info(f"Job {job_id} completed successfully")
            return {"status": "completed", "job_id": job_id}
            
        else:
            # Unexpected result
            supabase_client.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.FAILED,
                result={
                    "error_details": {
                        "message": "Unexpected workflow result",
                        "result": result
                    }
                }
            )
            
            logger.error(f"Job {job_id} failed with unexpected result: {result}")
            return {"status": "error", "message": "Unexpected workflow result"}
            
    except Exception as e:
        logger.exception(f"Error resuming job {job_id}: {e}")
        # Task will be retried or marked as failed by BaseJobTask.on_failure
        raise
