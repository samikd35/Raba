"""
Database-first job status tracking service.
Replaces in-memory JOB_STATUS_STORE with persistent database tracking.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from src.mint.api.system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobStatusService:
    """Service for managing job status in database across multiple server instances."""
    
    def __init__(self, use_service_role: bool = True):
        self.client = get_supabase_client(use_service_role=use_service_role)
    
    def create_job(
        self, 
        job_id: str, 
        user_id: str, 
        job_type: str = "problem_generation",
        initial_message: str = "Job created"
    ) -> bool:
        """Create a new job status record."""
        try:
            result = self.client.client.table("job_status").insert({
                "job_id": job_id,
                "user_id": user_id,
                "status": JobStatus.PENDING,
                "progress": 0,
                "message": initial_message,
                "job_type": job_type,
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None
            }).execute()
            
            if result.data:
                logger.info(f"Created job status record for {job_id}")
                return True
            else:
                logger.error(f"Failed to create job status record for {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating job status for {job_id}: {str(e)}")
            return False
    
    def update_job_status(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update job status atomically."""
        try:
            update_data = {}
            
            if status is not None:
                update_data["status"] = status
                
                # Set timestamps based on status
                if status == JobStatus.PROCESSING and not self._has_started(job_id):
                    update_data["started_at"] = datetime.utcnow().isoformat()
                elif status == JobStatus.COMPLETED:
                    update_data["completed_at"] = datetime.utcnow().isoformat()
            
            if progress is not None:
                update_data["progress"] = max(0, min(100, progress))
            
            if message is not None:
                update_data["message"] = message
                
            if error_message is not None:
                update_data["error_message"] = error_message
            
            if not update_data:
                return True  # Nothing to update
            
            result = self.client.client.table("job_status").update(update_data).eq("job_id", job_id).execute()
            
            if result.data:
                logger.info(f"Updated job {job_id}: {update_data}")
                return True
            else:
                logger.warning(f"No job found to update: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {str(e)}")
            return False
    
    def get_job_status(self, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get current job status from database."""
        try:
            query = self.client.client.table("job_status").select("*").eq("job_id", job_id)
            
            # Add user filter if provided (for RLS compliance)
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                job_data = result.data[0]
                logger.debug(f"Retrieved job status for {job_id}: {job_data['status']}")
                return job_data
            else:
                logger.debug(f"Job {job_id} not found in database")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving job status for {job_id}: {str(e)}")
            return None
    
    def mark_job_completed_with_results(self, job_id: str, results_count: int) -> bool:
        """
        Atomically mark job as completed only after results are verified in database.
        This prevents the race condition.
        """
        try:
            # First verify session exists and has been updated to completed
            session_check = self.client.client.table("problem_generation_sessions").select("session_id, status, problems_generated").eq("session_id", job_id).execute()
            
            if not session_check.data:
                logger.warning(f"Cannot mark job {job_id} as completed - session not found in database")
                return False
            
            session_data = session_check.data[0]
            session_status = session_data.get("status")
            problems_generated = session_data.get("problems_generated", 0)
            
            # Only mark as completed if session is completed and has problems
            if session_status != "completed" or problems_generated == 0:
                logger.warning(f"Cannot mark job {job_id} as completed - session status: {session_status}, problems: {problems_generated}")
                return False
            
            # Double-check by verifying problem statements exist
            problems_check = self.client.client.table("problem_statements").select("id").eq("session_id", job_id).execute()
            actual_problems_count = len(problems_check.data) if problems_check.data else 0
            
            if actual_problems_count == 0:
                logger.warning(f"Cannot mark job {job_id} as completed - no problem statements found in database")
                return False
            
            # Only mark completed if results actually exist
            success = self.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message=f"Generation completed with {actual_problems_count} problems"
            )
            
            if success:
                logger.info(f"Job {job_id} marked as completed with {actual_problems_count} problems verified")
            
            return success
            
        except Exception as e:
            logger.error(f"Error marking job {job_id} as completed: {str(e)}")
            return False
    
    def mark_job_failed(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed with error message."""
        return self.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            message="Job failed",
            error_message=error_message
        )
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        return self.update_job_status(
            job_id=job_id,
            status=JobStatus.CANCELLED,
            message="Job cancelled by user"
        )
    
    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """Clean up old job status records."""
        try:
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            result = self.client.client.table("job_status").delete().lt("created_at", cutoff_date.isoformat()).execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Cleaned up {deleted_count} old job status records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {str(e)}")
            return 0
    
    def _has_started(self, job_id: str) -> bool:
        """Check if job has already been started."""
        try:
            result = self.client.client.table("job_status").select("started_at").eq("job_id", job_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["started_at"] is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if job {job_id} has started: {str(e)}")
            return False

# Global instance
_job_status_service = None

def get_job_status_service() -> JobStatusService:
    """Get singleton job status service instance."""
    global _job_status_service
    if _job_status_service is None:
        _job_status_service = JobStatusService(use_service_role=True)
    return _job_status_service
