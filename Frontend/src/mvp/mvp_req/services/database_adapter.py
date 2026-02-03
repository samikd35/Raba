"""
Database Adapter for MVP Requirements Generator (AMRG)

Extends MVPDatabaseAdapter with AMRG-specific operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from src.mvp.adapters.database_adapter import MVPDatabaseAdapter
from ..models.enums import RunStatus
from ..models.state_models import AMRGRunRecord, AMRGQnARecord, AMRGOutputRecord

logger = logging.getLogger(__name__)


class AMRGDatabaseAdapter(MVPDatabaseAdapter):
    """
    Database adapter for AMRG operations.
    
    Extends MVPDatabaseAdapter with methods for:
    - AMRG run management
    - Q&A storage
    - PRD output versioning
    """
    
    def __init__(self, use_service_role: bool = True):
        """Initialize AMRG database adapter."""
        super().__init__(use_service_role=use_service_role)
        logger.info("AMRG Database Adapter initialized")
    
    # ==================== AMRG RUN OPERATIONS ====================
    
    def save_amrg_run(
        self,
        project_id: str,
        tenant_id: str,
        run_data: Dict[str, Any]
    ) -> bool:
        """
        Save AMRG run data to project.
        
        Stores in mvp_data.amrg.runs[run_id]
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_data: Run data including run_id, status, etc.
            
        Returns:
            True if successful
        """
        try:
            run_id = run_data.get("run_id")
            logger.info(f"Saving AMRG run {run_id} for project {project_id}")
            
            # Get current MVP data
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            
            # Initialize AMRG structure if needed
            if "amrg" not in mvp_data:
                mvp_data["amrg"] = {
                    "runs": {},
                    "current_run_id": None,
                    "output_versions": []
                }
            
            # Store run data
            mvp_data["amrg"]["runs"][run_id] = run_data
            mvp_data["amrg"]["current_run_id"] = run_id
            mvp_data["amrg"]["updated_at"] = datetime.utcnow().isoformat()
            
            # Save to database
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Saved AMRG run {run_id}")
            else:
                logger.error(f"❌ Failed to save AMRG run {run_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving AMRG run: {e}")
            traceback.print_exc()
            return False
    
    def get_amrg_run(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get AMRG run data by ID.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_id: AMRG run ID
            
        Returns:
            Run data or None
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            runs = amrg_data.get("runs", {})
            
            run_data = runs.get(run_id)
            if run_data:
                logger.info(f"Retrieved AMRG run {run_id}")
            else:
                logger.warning(f"AMRG run {run_id} not found")
            
            return run_data
            
        except Exception as e:
            logger.error(f"Error getting AMRG run: {e}")
            return None
    
    def get_current_amrg_run(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the current/latest AMRG run for a project."""
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            current_run_id = amrg_data.get("current_run_id")
            
            if current_run_id:
                return amrg_data.get("runs", {}).get(current_run_id)
            return None
            
        except Exception as e:
            logger.error(f"Error getting current AMRG run: {e}")
            return None
    
    def update_amrg_status(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str,
        status: RunStatus,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update AMRG run status.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_id: AMRG run ID
            status: New status
            additional_data: Optional additional fields to update
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Updating AMRG run {run_id} status to {status.value}")
            
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            runs = amrg_data.get("runs", {})
            
            if run_id not in runs:
                logger.error(f"Run {run_id} not found")
                return False
            
            # Update status
            runs[run_id]["status"] = status.value
            runs[run_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # Set completed_at if terminal status
            if status in [RunStatus.COMPLETED, RunStatus.FAILED]:
                runs[run_id]["completed_at"] = datetime.utcnow().isoformat()
            
            # Merge additional data
            if additional_data:
                runs[run_id].update(additional_data)
            
            mvp_data["amrg"]["runs"] = runs
            mvp_data["amrg"]["updated_at"] = datetime.utcnow().isoformat()
            
            # Save
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Updated AMRG run {run_id} status to {status.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating AMRG status: {e}")
            traceback.print_exc()
            return False
    
    # ==================== Q&A OPERATIONS ====================
    
    def save_amrg_questions(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str,
        questions: List[Dict[str, Any]]
    ) -> bool:
        """
        Save clarifying questions for a run.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_id: AMRG run ID
            questions: List of question dicts
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Saving {len(questions)} questions for run {run_id}")
            
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            runs = mvp_data.get("amrg", {}).get("runs", {})
            
            if run_id not in runs:
                logger.error(f"Run {run_id} not found")
                return False
            
            runs[run_id]["clarifying_questions"] = questions
            runs[run_id]["updated_at"] = datetime.utcnow().isoformat()
            
            mvp_data["amrg"]["runs"] = runs
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving questions: {e}")
            return False
    
    def save_amrg_answers(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str,
        answers: List[Dict[str, Any]]
    ) -> bool:
        """
        Save answers to clarifying questions.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_id: AMRG run ID
            answers: List of answer dicts with q_index and answer_text
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Saving {len(answers)} answers for run {run_id}")
            
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            runs = mvp_data.get("amrg", {}).get("runs", {})
            
            if run_id not in runs:
                logger.error(f"Run {run_id} not found")
                return False
            
            # Add timestamp to answers
            for answer in answers:
                answer["answered_at"] = datetime.utcnow().isoformat()
            
            runs[run_id]["clarifying_answers"] = answers
            runs[run_id]["updated_at"] = datetime.utcnow().isoformat()
            
            mvp_data["amrg"]["runs"] = runs
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error saving answers: {e}")
            return False
    
    # ==================== OUTPUT OPERATIONS ====================
    
    def save_amrg_output(
        self,
        project_id: str,
        tenant_id: str,
        run_id: str,
        prd_json: Dict[str, Any],
        validation_report: Dict[str, Any]
    ) -> bool:
        """
        Save PRD JSON output with versioning.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            run_id: AMRG run ID
            prd_json: Generated PRD JSON
            validation_report: Schema validation report
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Saving PRD output for run {run_id}")
            
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            runs = amrg_data.get("runs", {})
            
            if run_id not in runs:
                logger.error(f"Run {run_id} not found")
                return False
            
            # Determine version number
            output_versions = amrg_data.get("output_versions", [])
            version = len(output_versions) + 1
            
            # Create output record
            output_record = {
                "version": version,
                "run_id": run_id,
                "prd_json": prd_json,
                "validation_report": validation_report,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Add to versions list
            output_versions.append(output_record)
            amrg_data["output_versions"] = output_versions
            amrg_data["current_prd"] = prd_json
            amrg_data["current_prd_version"] = version
            
            # Update run with output reference
            runs[run_id]["prd_json"] = prd_json
            runs[run_id]["validation_report"] = validation_report
            runs[run_id]["output_version"] = version
            runs[run_id]["status"] = RunStatus.COMPLETED.value
            runs[run_id]["completed_at"] = datetime.utcnow().isoformat()
            
            amrg_data["runs"] = runs
            mvp_data["amrg"] = amrg_data
            
            response = self.supabase.client.table('vmp_projects').update({
                'mvp_data': mvp_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"✅ Saved PRD output version {version} for run {run_id}")
                
                # 📊 WORKFLOW STATUS: Mark MVP Requirements as completed
                try:
                    from src.vpm.services.workflow_status_service import get_workflow_status_service, WorkflowStage
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.MVP_REQUIREMENTS,
                        additional_metadata={"prd_version": version, "run_id": run_id}
                    )
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
                
                # 🔄 BACKGROUND CHUNKING: Chunk MVP requirements for "Chat with Project" feature
                try:
                    import asyncio
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    asyncio.create_task(
                        chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.MVP_REQUIREMENTS,
                            feature_data={"mvp_requirements": prd_json}
                        )
                    )
                    logger.info(f"🚀 Background chunking spawned for MVP requirements (AMRG)")
                except Exception as chunk_error:
                    logger.warning(f"⚠️ Background chunking failed (non-blocking): {chunk_error}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving PRD output: {e}")
            traceback.print_exc()
            return False
    
    def get_amrg_output(
        self,
        project_id: str,
        tenant_id: str,
        version: Optional[int] = None,
        run_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get PRD output by version, run_id, or latest.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            version: Optional version number (None = latest)
            run_id: Optional run_id UUID to fetch specific run output
            
        Returns:
            Output record or None
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            output_versions = amrg_data.get("output_versions", [])
            
            if not output_versions:
                return None
            
            # Search by run_id if provided
            if run_id:
                for output in output_versions:
                    if output.get("run_id") == run_id:
                        return output
                return None
            
            # Search by version number if provided
            if version is not None:
                for output in output_versions:
                    if output.get("version") == version:
                        return output
                return None
            
            # Return latest
            return output_versions[-1]
                
        except Exception as e:
            logger.error(f"Error getting PRD output: {e}")
            return None
    
    def get_amrg_history(
        self,
        project_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get PRD output version history.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            List of output version summaries
        """
        try:
            mvp_data = self.get_mvp_data(project_id, tenant_id)
            amrg_data = mvp_data.get("amrg", {})
            output_versions = amrg_data.get("output_versions", [])
            current_version = amrg_data.get("current_prd_version", 0)
            
            # Return summaries (without full PRD JSON)
            history = []
            for output in output_versions:
                history.append({
                    "version": output.get("version"),
                    "run_id": output.get("run_id"),
                    "template_code": output.get("prd_json", {}).get("template_code"),
                    "created_at": output.get("created_at"),
                    "validation_status": output.get("validation_report", {}).get("status"),
                    "is_current": output.get("version") == current_version
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting AMRG history: {e}")
            return []


# Singleton instance
_amrg_db_adapter: Optional[AMRGDatabaseAdapter] = None


def get_amrg_database_adapter() -> AMRGDatabaseAdapter:
    """Get singleton instance of AMRG database adapter."""
    global _amrg_db_adapter
    if _amrg_db_adapter is None:
        _amrg_db_adapter = AMRGDatabaseAdapter(use_service_role=True)
    return _amrg_db_adapter
