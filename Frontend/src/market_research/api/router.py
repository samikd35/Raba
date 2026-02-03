"""
Data Analysis Agent API Router

API endpoints for market research analysis following VMP patterns.
Integrates with existing VMP workflow as Phase 6.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

import uuid
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     Request, UploadFile)
from fastapi.responses import PlainTextResponse
from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import CreditService

# Credit service for market research analysis
credit_service = CreditService()

logger = logging.getLogger(__name__)

from src.mint.api.audit.models import AuditLogAction
from src.mint.api.audit.security import SecurityMonitor
# Import Yuba's existing security infrastructure
from src.mint.api.system.middleware.rate_limiter import RateLimiter
# VMP pattern imports - use existing VPM adapters
from src.vpm.adapters.auth_adapter import get_yuba_auth_adapter


# Proper security service implementation using Yuba's infrastructure
class VMPSecurityService:
    """Production-grade security service leveraging Yuba's existing infrastructure"""
    
    def __init__(self, auth_adapter):
        self.auth_adapter = auth_adapter
        # Initialize rate limiters for different operations
        self.rate_limiters = {
            'file_upload': RateLimiter(window_size=300, max_requests=10),  # 10 uploads per 5 min
            'analysis_execution': RateLimiter(window_size=600, max_requests=5),  # 5 analyses per 10 min
            'api_general': RateLimiter(window_size=60, max_requests=100)  # 100 requests per minute
        }
        self.security_monitor = SecurityMonitor()
    
    async def validate_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """Validate tenant access using Yuba auth adapter with security logging"""
        try:
            access_granted = await self.auth_adapter.validate_tenant_access(user_id, tenant_id)
            
            # Log security event using existing audit action
            await self.security_monitor.track_action_for_security(
                admin_user_id=user_id,
                action=AuditLogAction.SECURITY_ALERT if not access_granted else AuditLogAction.USER_ROLE_ADD,
                ip_address=None,  # Will be populated from request context
                success=access_granted
            )
            
            return access_granted
            
        except Exception as e:
            logger.error(f"Tenant access validation failed for user {user_id}, tenant {tenant_id}: {e}")
            return False
    
    async def check_rate_limit(self, user_id: str, operation: str, request) -> None:
        """Enforce rate limiting using Yuba's rate limiter"""
        # Get client IP for rate limiting
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_key = f"{user_id}:{client_ip}"
        
        # Check rate limit for the specific operation
        rate_limiter = self.rate_limiters.get(operation, self.rate_limiters['api_general'])
        is_limited, remaining = rate_limiter.is_rate_limited(rate_limit_key)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for user {user_id} from {client_ip} on operation {operation}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded for {operation}. Try again later.",
                    "retry_after": rate_limiter.window_size
                }
            )
        
        logger.debug(f"Rate limit check passed for {user_id}:{operation} - {remaining} requests remaining")
    
    async def log_project_access(self, **kwargs) -> None:
        """Log project access events for audit trail"""
        try:
            user_id = kwargs.get('user_id')
            project_id = kwargs.get('project_id')
            operation = kwargs.get('operation', 'unknown')
            details = kwargs.get('details', {})
            
            # Create audit log entry
            audit_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'project_id': project_id,
                'operation': operation,
                'module': 'market_research_analysis',
                'details': details
            }
            
            logger.info(f"PROJECT_ACCESS: {audit_data}")
            
            # Track for security monitoring using existing audit action
            if user_id:
                await self.security_monitor.track_action_for_security(
                    admin_user_id=user_id,
                    action=AuditLogAction.DATA_EXPORT,  # Closest existing action for project access
                    ip_address=details.get('client_ip'),
                    success=True
                )
                
        except Exception as e:
            logger.error(f"Failed to log project access: {e}")

from ..adapters.auth_adapter import AnalysisAgentAuthAdapter
from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
# Enterprise analysis service imports
from ..services.market_research_analysis_service import \
    EnterpriseMarketResearchService, BatchProcessingConfig, ProcessingUpdate
# API models
from .models import (AnalysisError, AnalysisExecutionRequest,
                     AnalysisExecutionResponse, AnalysisProgress,
                     AnalysisResultsResponse, AnalysisStatusResponse,
                     DocumentProcessingStatus, FileUploadResponse,
                     ResearchDocumentInfo, DocumentDeleteResponse,
                     BulkDocumentDeleteResponse)

# Create router following VMP patterns
analysis_router = APIRouter(prefix="/analysis", tags=["market-research-analysis"])

logger.info("🔍 ROUTER DEBUG: Market Research Analysis router created")
logger.info(f"🔍 ROUTER DEBUG: Router prefix: {analysis_router.prefix}")
logger.info(f"🔍 ROUTER DEBUG: Router tags: {analysis_router.tags}")

# Import monitoring endpoints
logger.info("🔍 ROUTER DEBUG: Importing monitoring endpoints...")
from .monitoring_endpoints import monitoring_router

# Include monitoring router
logger.info("🔍 ROUTER DEBUG: Including monitoring router...")
analysis_router.include_router(monitoring_router)
logger.info(f"🔍 ROUTER DEBUG: Monitoring router included. Total routes so far: {len(analysis_router.routes)}")

# Import chat endpoints
logger.info("🔍 ROUTER DEBUG: Importing chat endpoints...")
from .chat_endpoints import chat_router

# Include chat router
logger.info("🔍 ROUTER DEBUG: Including chat router...")
analysis_router.include_router(chat_router)
logger.info(f"🔍 ROUTER DEBUG: Chat router included. Total routes so far: {len(analysis_router.routes)}")

# Dependency injection following VMP patterns
def get_analysis_service() -> EnterpriseMarketResearchService:
    """Get enterprise market research analysis service instance"""
    return EnterpriseMarketResearchService()

def get_database_adapter() -> AnalysisAgentDatabaseAdapter:
    """Get database adapter instance"""
    return AnalysisAgentDatabaseAdapter(use_service_role=True)

def get_auth_adapter() -> AnalysisAgentAuthAdapter:
    """Get auth adapter instance"""
    return AnalysisAgentAuthAdapter()

def get_security_service() -> VMPSecurityService:
    """Get VMP security service for consistent security patterns"""
    auth_adapter = get_yuba_auth_adapter()
    return VMPSecurityService(auth_adapter)


# ---------- File Upload Endpoints ----------

@analysis_router.post("/projects/{project_id}/upload-documents", response_model=FileUploadResponse)
async def upload_research_documents(
    project_id: str,
    request: Request,
    pdf_files: Union[List[UploadFile], UploadFile, List[str], str, None] = File(default=None, description="PDF research documents (up to 25)"),
    csv_files: Union[List[UploadFile], UploadFile, List[str], str, None] = File(default=None, description="CSV research data (up to 5)"),
    persona_id: Optional[str] = Form(None, description="Persona ID for multi-persona projects (required if project has multiple personas)"),
    enable_enhanced_processing: bool = Form(True, description="Use enhanced processing pipeline with statistics registry"),
    extract_statistics: bool = Form(True, description="Pre-compute statistics registry for accurate analysis"),
    enable_fact_validation: bool = Form(True, description="Enable fact validation for uploaded documents"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and process research documents (PDF interviews, CSV surveys).
    
    This endpoint handles multipart/form-data uploads with file validation,
    size limits, and security checks. Documents are processed, chunked,
    and embedded for analysis.
    
    **Requirements**: 8.2, 8.3, 10.1
    """
    try:
        logger.info(f"📤 UPLOAD: Starting document upload for project {project_id}")
        
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found or inaccessible"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_project",
                    "message": "Project missing required tenant_id or user_id"
                }
            )
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required and valid
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        logger.info(f"📋 PERSONA CHECK: Project has {len(project_personas)} persona(s)")
        
        # If project has multiple personas, persona_id is required
        if len(project_personas) > 1:
            if not persona_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "persona_id_required",
                        "message": f"This project has {len(project_personas)} personas. You must specify which persona this research data belongs to.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            # Validate persona_id exists in project
            valid_persona_ids = [p.get("id") for p in project_personas]
            if persona_id not in valid_persona_ids:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' not found in project.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            logger.info(f"✅ PERSONA VALIDATION: Using persona '{persona_id}' for document upload")
        
        # If project has single persona, use it automatically
        elif len(project_personas) == 1:
            if not persona_id:
                persona_id = project_personas[0].get("id")
                logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}'")
            elif persona_id != project_personas[0].get("id"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' does not match project's persona '{project_personas[0].get('id')}'.",
                        "available_personas": [{"id": project_personas[0].get("id"), "name": project_personas[0].get("name")}]
                    }
                )
        
        # If no personas exist yet, this is an error
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_personas_found",
                    "message": "Project must have at least one persona before uploading research documents. Please complete persona identification first."
                }
            )
        
        
        # ROBUST INPUT NORMALIZATION: Handle all possible input types
        def normalize_file_input(files, file_type_name):
            """Normalize file input to a list of UploadFile objects."""
            if files is None:
                return []
            elif isinstance(files, str):
                # Frontend sent string placeholder when no files selected
                return []
            elif hasattr(files, 'filename'):
                # Single UploadFile object
                return [files]
            elif isinstance(files, list):
                # Already a list, filter out any invalid entries
                valid_files = []
                for f in files:
                    if hasattr(f, 'filename'):
                        valid_files.append(f)
                    elif isinstance(f, str):
                        # Skip strings silently (common when frontend sends empty form fields)
                        continue
                    else:
                        # Skip invalid objects silently
                        continue
                return valid_files
            else:
                # Unknown input type, convert to empty list
                return []
        
        pdf_files = normalize_file_input(pdf_files, "PDF")
        csv_files = normalize_file_input(csv_files, "CSV")
        
        logger.info(f"📄 UPLOAD: Processing {len(pdf_files)} PDF files and {len(csv_files)} CSV files")
        
        # Validate tenant access and rate limiting (following VMP patterns)
        await security_service.validate_tenant_access(user_id, tenant_id)
        await security_service.check_rate_limit(user_id, 'file_upload', request)
        
        # Validate at least one file is provided
        total_files = len(pdf_files) + len(csv_files)
        if total_files == 0:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "At least one file must be provided. You can upload PDF files only, CSV files only, or both types together.",
                    "field": "files"
                }
            )
        
        # Validate file count limits
        if len(pdf_files) > 25:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "Maximum 25 PDF files allowed",
                    "field": "pdf_files"
                }
            )
        
        if len(csv_files) > 5:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "Maximum 5 CSV files allowed",
                    "field": "csv_files"
                }
            )
        
        # Validate file types and sizes (reduced for memory safety)
        max_file_size = 25 * 1024 * 1024  # 25MB limit to prevent memory issues
        allowed_pdf_types = ["application/pdf"]
        allowed_csv_types = ["text/csv", "application/csv", "text/plain"]
        
        uploaded_files = []
        
        # Validate PDF files
        for i, pdf_file in enumerate(pdf_files):
            if pdf_file.content_type not in allowed_pdf_types:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "validation_error",
                        "message": f"Invalid PDF file type: {pdf_file.content_type}",
                        "field": f"pdf_files[{i}]"
                    }
                )
            
            if pdf_file.size > max_file_size:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "validation_error",
                        "message": f"PDF file too large: {pdf_file.size} bytes (max: {max_file_size})",
                        "field": f"pdf_files[{i}]"
                    }
                )
            
            uploaded_files.append({
                "type": "pdf",
                "filename": pdf_file.filename,
                "size": pdf_file.size,
                "content_type": pdf_file.content_type,
                "index": i
            })
        
        # Validate CSV files
        for i, csv_file in enumerate(csv_files):
            if csv_file.content_type not in allowed_csv_types:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "validation_error",
                        "message": f"Invalid CSV file type: {csv_file.content_type}",
                        "field": f"csv_files[{i}]"
                    }
                )
            
            if csv_file.size > max_file_size:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "validation_error",
                        "message": f"CSV file too large: {csv_file.size} bytes (max: {max_file_size})",
                        "field": f"csv_files[{i}]"
                    }
                )
            
            uploaded_files.append({
                "type": "csv",
                "filename": csv_file.filename,
                "size": csv_file.size,
                "content_type": csv_file.content_type,
                "index": i
            })
        
        # ENHANCED FILE REPLACEMENT LOGIC: Check for existing files and handle duplicates
        logger.info("🔍 FILE REPLACEMENT: Checking for existing files in database...")
        
        # Get existing research documents data
        db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        existing_research_data = await db_adapter.get_research_documents_data(project_id, tenant_id)
        
        # Track file operations for logging
        file_operations = {
            "replaced_files": [],
            "new_files": [],
            "existing_files_kept": []
        }
        
        if existing_research_data:
            logger.info(f"🔍 FILE REPLACEMENT: Found existing research data with {len(existing_research_data)} document entries")
            
            # MULTI-PERSONA FIX: Create filename mapping for existing files ONLY for the current persona
            existing_filenames = {}
            for doc_key, doc_data in existing_research_data.items():
                if isinstance(doc_data, dict) and "metadata" in doc_data:
                    filename = doc_data["metadata"].get("filename")
                    doc_persona_id = doc_data["metadata"].get("persona_id")
                    
                    # Only consider files from the SAME persona for replacement
                    if filename and doc_persona_id == persona_id:
                        existing_filenames[filename] = doc_key
                        logger.info(f"🔍 FILE REPLACEMENT: Existing file found for persona '{persona_id}' - {filename} (key: {doc_key})")
                    elif filename and doc_persona_id != persona_id:
                        logger.info(f"🎭 PERSONA FILTER: Skipping file '{filename}' (belongs to persona '{doc_persona_id}', not '{persona_id}')")
            
            # Check PDF files for duplicates
            pdf_files_to_process = []
            for pdf_file in pdf_files:
                if pdf_file.filename in existing_filenames:
                    file_operations["replaced_files"].append({
                        "filename": pdf_file.filename,
                        "type": "pdf",
                        "action": "replaced",
                        "existing_key": existing_filenames[pdf_file.filename]
                    })
                    logger.info(f"🔄 FILE REPLACEMENT: PDF file '{pdf_file.filename}' will REPLACE existing file")
                else:
                    file_operations["new_files"].append({
                        "filename": pdf_file.filename,
                        "type": "pdf",
                        "action": "added"
                    })
                    logger.info(f"➕ FILE REPLACEMENT: PDF file '{pdf_file.filename}' will be ADDED as new file")
                pdf_files_to_process.append(pdf_file)
            
            # Check CSV files for duplicates  
            csv_files_to_process = []
            for csv_file in csv_files:
                if csv_file.filename in existing_filenames:
                    file_operations["replaced_files"].append({
                        "filename": csv_file.filename,
                        "type": "csv", 
                        "action": "replaced",
                        "existing_key": existing_filenames[csv_file.filename]
                    })
                    logger.info(f"🔄 FILE REPLACEMENT: CSV file '{csv_file.filename}' will REPLACE existing file")
                else:
                    file_operations["new_files"].append({
                        "filename": csv_file.filename,
                        "type": "csv",
                        "action": "added"
                    })
                    logger.info(f"➕ FILE REPLACEMENT: CSV file '{csv_file.filename}' will be ADDED as new file")
                csv_files_to_process.append(csv_file)
            
            # Track files that will be kept (not being replaced) - ONLY for current persona
            uploaded_filenames = set([f.filename for f in pdf_files + csv_files])
            for doc_key, doc_data in existing_research_data.items():
                if isinstance(doc_data, dict) and "metadata" in doc_data:
                    filename = doc_data["metadata"].get("filename")
                    doc_persona_id = doc_data["metadata"].get("persona_id")
                    
                    # Only track kept files for the SAME persona
                    if filename and doc_persona_id == persona_id and filename not in uploaded_filenames:
                        file_operations["existing_files_kept"].append({
                            "filename": filename,
                            "existing_key": doc_key,
                            "action": "kept"
                        })
                        logger.info(f"📁 FILE REPLACEMENT: Existing file '{filename}' (persona '{persona_id}') will be KEPT (not replaced)")
            
            # Update file lists to process
            pdf_files = pdf_files_to_process
            csv_files = csv_files_to_process
            
        else:
            logger.info("🆕 FILE REPLACEMENT: No existing research data found, all files will be new")
            for pdf_file in pdf_files:
                file_operations["new_files"].append({
                    "filename": pdf_file.filename,
                    "type": "pdf",
                    "action": "added"
                })
            for csv_file in csv_files:
                file_operations["new_files"].append({
                    "filename": csv_file.filename,
                    "type": "csv",
                    "action": "added"
                })

        # Process documents using analysis service with timeout protection
        try:
            # FORCE ENHANCED PROCESSING: Always use enhanced method for new uploads
            try:
                use_enhanced = enable_enhanced_processing
                logger.info(f"🔍 DEBUG: Enhanced processing parameter received: {use_enhanced}")
            except NameError:
                # Parameter doesn't exist (server not restarted), force enhanced processing
                use_enhanced = True
                logger.info("🚀 FORCE: Enhanced processing parameter missing, defaulting to TRUE")
            
            if use_enhanced:
                logger.info(f"🚀 FORCED: Using enhanced document processing with statistics registry and file replacement for persona '{persona_id}'")
                result = await asyncio.wait_for(
                    analysis_service._process_research_documents_enhanced_with_replacement(
                        project_id, tenant_id, pdf_files, csv_files, existing_research_data, file_operations, persona_id=persona_id, user_id=user_id
                    ),
                    timeout=300.0  # 5 minute timeout
                )
            else:
                # Enhanced processing is always enabled
                logger.info("Enhanced processing is always enabled")
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail={
                    "error": "processing_timeout",
                    "message": "Document processing timed out. Please try with smaller files or fewer files.",
                    "suggestions": [
                        "Reduce file size",
                        "Upload fewer files at once",
                        "Try splitting large documents"
                    ]
                }
            )
        
        if not result["success"]:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": result.get("error_code", "processing_error"),
                    "message": result["error"]
                }
            )
        
        # Calculate processing statistics
        research_data = result["data"]
        total_chunks = 0
        processing_status = {}
        
        # Process PDF statistics
        for i in range(len(pdf_files)):
            pdf_key = f"pdf_content_{i}" if i > 0 else "pdf_content"
            if pdf_key in research_data:
                pdf_entry = research_data[pdf_key]
                pdf_chunks = pdf_entry.get("chunk_count")
                if pdf_chunks is None:
                    if isinstance(pdf_entry.get("chunks"), list):
                        pdf_chunks = len(pdf_entry["chunks"])
                    elif isinstance(pdf_entry.get("chunk_metadata"), list):
                        pdf_chunks = len(pdf_entry["chunk_metadata"])
                    else:
                        pdf_chunks = 0
                total_chunks += pdf_chunks
                processing_status[f"pdf_{i}"] = {
                    "status": "completed",
                    "chunks": pdf_chunks,
                    "filename": pdf_files[i].filename,
                    "updated_at": datetime.utcnow().isoformat()
                }
        
        # Process CSV statistics
        for i in range(len(csv_files)):
            csv_key = f"csv_content_{i}" if i > 0 else "csv_content"
            if csv_key in research_data:
                csv_entry = research_data[csv_key]
                csv_chunks = csv_entry.get("chunk_count")
                if csv_chunks is None:
                    if isinstance(csv_entry.get("chunks"), list):
                        csv_chunks = len(csv_entry["chunks"])
                    elif isinstance(csv_entry.get("chunk_metadata"), list):
                        csv_chunks = len(csv_entry["chunk_metadata"])
                    else:
                        csv_chunks = 0
                total_chunks += csv_chunks
                processing_status[f"csv_{i}"] = {
                    "status": "completed",
                    "chunks": csv_chunks,
                    "filename": csv_files[i].filename,
                    "updated_at": datetime.utcnow().isoformat()
                }
        
        # Log file upload for audit
        await security_service.log_project_access(
            user_id=user_id,
            project_id=project_id,
            operation='upload_research_documents',
            details={
                'uploaded_files': [f["filename"] for f in uploaded_files],
                'total_chunks': total_chunks,
                'file_sizes': {f["filename"]: f["size"] for f in uploaded_files}
            }
        )
        
        # Prepare response message based on file operations
        if file_operations:
            replaced_count = len(file_operations.get("replaced_files", []))
            new_count = len(file_operations.get("new_files", []))
            kept_count = len(file_operations.get("existing_files_kept", []))
            
            if replaced_count > 0 and new_count > 0:
                message = f"Successfully processed {len(uploaded_files)} file(s): {replaced_count} replaced, {new_count} added. {kept_count} existing files kept."
            elif replaced_count > 0:
                message = f"Successfully replaced {replaced_count} existing file(s). {kept_count} existing files kept."
            elif new_count > 0:
                message = f"Successfully added {new_count} new file(s). {kept_count} existing files kept."
            else:
                message = f"Successfully processed {len(uploaded_files)} file(s) with enhanced processing"
        else:
            message = f"Successfully uploaded and processed {len(uploaded_files)} file(s) with enhanced processing"

        # Add persona information to message if multi-persona project
        persona_info = next((p for p in project_personas if p.get("id") == persona_id), None)
        if len(project_personas) > 1 and persona_info:
            message = f"{message} [Persona: {persona_info.get('name', persona_id)}]"
        
        return FileUploadResponse(
            success=True,
            message=message,
            data={
                "project_id": project_id,
                "persona_id": persona_id,
                "persona_name": persona_info.get("name") if persona_info else None,
                "uploaded_files": [f["filename"] for f in uploaded_files],
                "processing_status": processing_status,
                "total_chunks": total_chunks,
                "uploaded_at": datetime.utcnow().isoformat(),
                "file_operations": file_operations,
                "enhanced_processing": {
                    "enabled": True,
                    "statistics_extraction": extract_statistics,
                    "fact_validation": True,
                    "file_replacement": True,
                    "processing_type": "enhanced_with_replacement",
                    "persona_aware": True
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "upload_error",
                "message": f"Failed to upload research documents: {str(e)}"
            }
        )


@analysis_router.get("/projects/{project_id}/documents")
async def get_uploaded_documents(
    project_id: str,
    persona_id: Optional[str] = Query(None, description="Optional: Filter documents by persona ID"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get information about uploaded research documents for a project.
    
    This endpoint returns metadata about uploaded documents including
    processing status, chunk counts, and file information.
    
    For multi-persona projects, optionally filter by persona_id to see
    only documents belonging to a specific persona.
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found or inaccessible"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_project",
                    "message": "Project missing required tenant_id or user_id"
                }
            )
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # Get research documents data from database (where it's actually stored)
        research_data = project_context.get("research_documents_data", {})
        
        # CRITICAL FIX: If not in context, load from database where upload stores it
        if not research_data:
            try:
                from src.market_research.adapters.database_adapter import AnalysisAgentDatabaseAdapter
                db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
                research_data = await db_adapter.get_research_documents_data(project_id, tenant_id)
                logger.info(f"🔍 DOCUMENTS: Loaded research data from database: {bool(research_data)}")
                if research_data:
                    logger.info(f"🔍 DOCUMENTS: Research data keys: {list(research_data.keys()) if isinstance(research_data, dict) else 'Not a dict'}")
                    logger.info(f"🔍 DOCUMENTS: Research data type: {type(research_data)}")
            except Exception as e:
                logger.error(f"❌ DOCUMENTS: Failed to load from database: {e}")
                research_data = {}
        
        if not research_data:
            logger.warning(f"🔍 DOCUMENTS: No research data found for project {project_id}")
            return {
                "project_id": project_id,
                "documents": [],
                "total_documents": 0,
                "total_chunks": 0
            }

        documents: List[ResearchDocumentInfo] = []
        total_chunks = 0

        manifest = research_data.get("documents_manifest", {}) if isinstance(research_data, dict) else {}
        manifest_entries = manifest.get("documents", []) if isinstance(manifest, dict) else []
        logger.info(f"🔍 DOCUMENTS: Manifest entries count: {len(manifest_entries)}")

        document_map = {
            key: value
            for key, value in research_data.items()
            if key not in ["documents_manifest", "statistics_registry"] and isinstance(value, dict)
        }
        logger.info(f"🔍 DOCUMENTS: Document map keys: {list(document_map.keys())}")

        # CRITICAL FIX: If no manifest but we have document data, create manifest from existing data
        if not manifest_entries and document_map:
            logger.info(f"🔧 DOCUMENTS: No manifest found, creating from existing document data")
            manifest_entries = []
            for doc_key, doc_data in document_map.items():
                if isinstance(doc_data, dict):
                    # Determine document type from key or metadata
                    doc_type = "csv" if "csv" in doc_key.lower() else "pdf"
                    filename = doc_data.get("metadata", {}).get("filename", f"{doc_key}.{doc_type}")
                    chunk_count = len(doc_data.get("chunks", [])) or doc_data.get("chunk_count", 0)
                    
                    manifest_entries.append({
                        "document_key": doc_key,
                        "document_type": doc_type,
                        "filename": filename,
                        "chunk_count": chunk_count,
                        "processing_timestamp": doc_data.get("processing_timestamp")
                    })
            logger.info(f"🔧 DOCUMENTS: Created manifest with {len(manifest_entries)} entries")

        processed_keys = set()

        def _resolve_chunk_count(doc: Dict[str, Any]) -> int:
            if isinstance(doc.get("chunks"), list):
                return len(doc.get("chunks", []))
            for key in ("total_chunks", "chunk_count"):
                if isinstance(doc.get(key), int):
                    return doc[key]
            return 0

        for entry in manifest_entries:
            if not isinstance(entry, dict):
                continue

            doc_key = entry.get("document_key")
            document_type = entry.get("document_type")
            if document_type not in ("pdf", "csv"):
                continue

            doc_data = document_map.get(doc_key, {})
            metadata = doc_data.get("metadata", {}) if isinstance(doc_data, dict) else {}
            filename = entry.get("filename") or metadata.get("filename") or doc_key or "unknown"
            file_size = entry.get("file_size") or metadata.get("file_size", 0)
            uploaded_at = metadata.get("uploaded_at") or entry.get("uploaded_at") or metadata.get("parsed_at") or datetime.utcnow().isoformat()
            chunk_count = entry.get("chunk_count") or _resolve_chunk_count(doc_data)

            total_chunks += chunk_count
            processed_keys.add(doc_key)

            documents.append(ResearchDocumentInfo(
                document_type=document_type,
                filename=filename,
                file_size=file_size,
                chunks_count=chunk_count,
                processing_status=DocumentProcessingStatus(
                    status="completed",
                    chunks=chunk_count,
                    updated_at=uploaded_at
                ),
                persona_id=metadata.get("persona_id"),  # MULTI-PERSONA: Include persona_id
                metadata=metadata or {}
            ))

        for doc_key, doc_data in document_map.items():
            if doc_key in processed_keys:
                continue

            metadata = doc_data.get("metadata", {}) if isinstance(doc_data, dict) else {}
            document_type = metadata.get("source_type")
            if document_type not in ("pdf", "csv"):
                continue

            filename = metadata.get("filename", doc_key)
            chunk_count = _resolve_chunk_count(doc_data)
            total_chunks += chunk_count

            documents.append(ResearchDocumentInfo(
                document_type=document_type,
                filename=filename,
                file_size=metadata.get("file_size", 0),
                chunks_count=chunk_count,
                processing_status=DocumentProcessingStatus(
                    status="completed",
                    chunks=chunk_count,
                    updated_at=metadata.get("uploaded_at", datetime.utcnow().isoformat())
                ),
                persona_id=metadata.get("persona_id"),  # MULTI-PERSONA: Include persona_id
                metadata=metadata
            ))

        # MULTI-PERSONA: Filter by persona_id if provided
        if persona_id:
            filtered_documents = [doc for doc in documents if doc.persona_id == persona_id]
            filtered_chunks = sum(doc.chunks_count for doc in filtered_documents)
            logger.info(f"🎭 DOCUMENTS FILTER: Filtered to {len(filtered_documents)} documents for persona '{persona_id}'")
            
            return {
                "project_id": project_id,
                "persona_id": persona_id,
                "documents": filtered_documents,
                "total_documents": len(filtered_documents),
                "total_chunks": filtered_chunks,
                "all_personas_total": len(documents)  # Include total for reference
            }
        
        # Group documents by persona for summary
        persona_summary = {}
        for doc in documents:
            p_id = doc.persona_id or "unknown"
            if p_id not in persona_summary:
                persona_summary[p_id] = {"count": 0, "chunks": 0}
            persona_summary[p_id]["count"] += 1
            persona_summary[p_id]["chunks"] += doc.chunks_count
        
        return {
            "project_id": project_id,
            "documents": documents,
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "by_persona": persona_summary  # NEW: Summary by persona
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document information: {str(e)}"
        )


# ---------- Document Management Endpoints ----------

@analysis_router.delete("/projects/{project_id}/documents/{filename}", response_model=DocumentDeleteResponse)
async def delete_individual_document(
    project_id: str,
    filename: str,
    request: Request,
    persona_id: Optional[str] = Query(None, description="Persona ID for multi-persona projects (required if project has multiple personas)"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific uploaded research document by filename.
    
    This endpoint removes a single document from the project's research data,
    including all associated chunks from both database and vector store. 
    The document is identified by its original filename.
    
    For multi-persona projects, specify persona_id to delete only the document
    belonging to that persona.
    
    Args:
        project_id: The VMP project ID
        filename: The original filename of the document to delete
        persona_id: Optional persona ID for multi-persona projects
        
    Returns:
        Success confirmation with details about the deleted document
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found or inaccessible"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_project",
                    "message": "Project missing required tenant or user information"
                }
            )
        
        # Rate limiting
        await security_service.check_rate_limit(user_id, "api_general", request)
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        if len(project_personas) > 1 and not persona_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "persona_id_required",
                    "message": f"This project has {len(project_personas)} personas. You must specify which persona's document to delete.",
                    "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                }
            )
        
        if len(project_personas) == 1 and not persona_id:
            persona_id = project_personas[0].get("id")
            logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}' for deletion")
        
        # Get current research documents data
        from src.market_research.adapters.database_adapter import AnalysisAgentDatabaseAdapter
        db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        research_data = await db_adapter.get_research_documents_data(project_id, tenant_id)
        
        if not research_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "no_documents_found",
                    "message": "No research documents found for this project"
                }
            )
        
        # Find the document to delete (persona-aware)
        document_found = False
        document_info = {}
        document_key_to_delete = None
        updated_research_data = research_data.copy()
        
        logger.info(f"🗑️ DELETE: Looking for document '{filename}' for persona '{persona_id}'")
        
        # Check manifest for the document
        manifest = research_data.get("documents_manifest", {})
        manifest_docs = manifest.get("documents", [])
        
        # Find and remove from manifest
        updated_manifest_docs = []
        for doc in manifest_docs:
            if doc.get("filename") == filename:
                document_found = True
                document_info = {
                    "filename": doc.get("filename"),
                    "document_type": doc.get("document_type"),
                    "file_size": doc.get("file_size", 0),
                    "upload_timestamp": doc.get("upload_timestamp")
                }
            else:
                updated_manifest_docs.append(doc)
        
        if document_found:
            # Update manifest
            updated_research_data["documents_manifest"] = {
                **manifest,
                "documents": updated_manifest_docs
            }
        
        # MULTI-PERSONA: Remove document data from research_data (only if persona matches)
        keys_to_remove = []
        for key, value in research_data.items():
            if key in ["documents_manifest", "statistics_registry"]:
                continue
                
            if isinstance(value, dict):
                metadata = value.get("metadata", {})
                doc_persona_id = metadata.get("persona_id")
                
                # Only delete if filename AND persona_id match
                if metadata.get("filename") == filename:
                    if persona_id and doc_persona_id != persona_id:
                        logger.info(f"🎭 PERSONA FILTER: Skipping document '{filename}' (belongs to persona '{doc_persona_id}', not '{persona_id}')")
                        continue
                    
                    keys_to_remove.append(key)
                    document_key_to_delete = key
                    document_found = True
                    if not document_info:  # If not found in manifest, get info from data
                        document_info = {
                            "filename": filename,
                            "document_type": metadata.get("document_type", "unknown"),
                            "file_size": metadata.get("file_size", 0),
                            "upload_timestamp": metadata.get("upload_timestamp"),
                            "persona_id": doc_persona_id
                        }
                    logger.info(f"✅ DELETE: Found document '{filename}' for persona '{persona_id}' (key: {key})")
        
        # Remove the document data
        for key in keys_to_remove:
            del updated_research_data[key]
        
        if not document_found:
            persona_msg = f" for persona '{persona_id}'" if persona_id else ""
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "document_not_found",
                    "message": f"Document '{filename}' not found{persona_msg} in project research data"
                }
            )
        
        # Delete chunks from vector database
        try:
            from src.market_research.services.vector_database_service import VectorDatabaseService
            vector_service = VectorDatabaseService()
            
            # Delete chunks by document key
            deleted_chunks = await vector_service.delete_document_chunks(
                project_id=project_id,
                tenant_id=tenant_id,
                document_key=document_key_to_delete
            )
            logger.info(f"🗑️ VECTOR DB: Deleted {deleted_chunks} chunks from vector database for document '{filename}'")
        except Exception as e:
            logger.warning(f"⚠️ VECTOR DB: Failed to delete chunks from vector database: {e}")
            # Continue with database update even if vector deletion fails
        
        # Update the database
        success = await db_adapter.update_research_documents_data(
            project_id, tenant_id, updated_research_data
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "delete_failed",
                    "message": "Failed to delete document from database"
                }
            )
        
        # Log the deletion
        await security_service.log_project_access(
            user_id=user_id,
            project_id=project_id,
            operation='delete_individual_document',
            details={
                'deleted_document': document_info,
                'remaining_documents': len(updated_manifest_docs)
            }
        )
        
        logger.info(f"✅ DOCUMENT DELETE: Successfully deleted '{filename}' from project {project_id}")
        
        return {
            "success": True,
            "message": f"Document '{filename}' successfully deleted",
            "deleted_document": document_info,
            "remaining_documents": len(updated_manifest_docs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"❌ DOCUMENT DELETE: Failed to delete document '{filename}': {str(e)}")
        logger.error(f"❌ DOCUMENT DELETE: Exception type: {type(e)}")
        logger.error(f"❌ DOCUMENT DELETE: Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "delete_error",
                "message": f"Failed to delete document: {str(e)}"
            }
        )


@analysis_router.delete("/projects/{project_id}/documents", response_model=BulkDocumentDeleteResponse)
async def delete_all_documents(
    project_id: str,
    persona_id: Optional[str] = Query(None, description="Persona ID for multi-persona projects (deletes only documents for this persona)"),
    request: Request = None,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete all uploaded research documents for a project (or for a specific persona).
    
    This endpoint removes documents from the project's research data,
    including all associated chunks from both database and vector store.
    
    For multi-persona projects:
    - If persona_id is provided: Deletes only documents for that persona
    - If persona_id is not provided: Requires confirmation (multi-persona projects must specify)
    
    Args:
        project_id: The VMP project ID
        persona_id: Optional persona ID to delete documents for specific persona only
        
    Returns:
        Success confirmation with details about deleted documents
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found or inaccessible"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_project",
                    "message": "Project missing required tenant or user information"
                }
            )
        
        # Rate limiting
        await security_service.check_rate_limit(user_id, "api_general", request)
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        if len(project_personas) > 1 and not persona_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "persona_id_required",
                    "message": f"This project has {len(project_personas)} personas. You must specify which persona's documents to delete, or delete each persona separately.",
                    "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                }
            )
        
        if len(project_personas) == 1 and not persona_id:
            persona_id = project_personas[0].get("id")
            logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}' for bulk deletion")
        
        # Get current research documents data to count what we're deleting
        from src.market_research.adapters.database_adapter import AnalysisAgentDatabaseAdapter
        db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        research_data = await db_adapter.get_research_documents_data(project_id, tenant_id)
        
        # MULTI-PERSONA: Count and collect documents to delete (filtered by persona if specified)
        deleted_count = 0
        deleted_documents = []
        keys_to_delete = []
        updated_research_data = research_data.copy() if research_data else {}
        
        if research_data:
            logger.info(f"🗑️ BULK DELETE: Deleting documents for persona '{persona_id}'")
            
            # Collect documents to delete from data keys (persona-aware)
            for key, value in research_data.items():
                if key in ["documents_manifest", "statistics_registry"]:
                    continue
                    
                if isinstance(value, dict):
                    metadata = value.get("metadata", {})
                    doc_persona_id = metadata.get("persona_id")
                    filename = metadata.get("filename")
                    
                    # Only delete if persona matches (or no persona filter)
                    if persona_id and doc_persona_id != persona_id:
                        logger.info(f"🎭 PERSONA FILTER: Keeping document '{filename}' (belongs to persona '{doc_persona_id}', not '{persona_id}')")
                        continue
                    
                    if filename:
                        keys_to_delete.append(key)
                        deleted_count += 1
                        deleted_documents.append({
                            "filename": filename,
                            "document_type": metadata.get("document_type", "unknown"),
                            "file_size": metadata.get("file_size", 0),
                            "persona_id": doc_persona_id
                        })
                        logger.info(f"✅ BULK DELETE: Marking '{filename}' for deletion (persona: {doc_persona_id})")
            
            # Remove marked documents
            for key in keys_to_delete:
                del updated_research_data[key]
            
            logger.info(f"🗑️ BULK DELETE: Marked {deleted_count} documents for deletion")
        
        if deleted_count == 0:
            persona_msg = f" for persona '{persona_id}'" if persona_id else ""
            return {
                "success": True,
                "message": f"No documents found to delete{persona_msg}",
                "deleted_documents": [],
                "deleted_count": 0
            }
        
        # Delete chunks from vector database for each document
        total_deleted_chunks = 0
        try:
            from src.market_research.services.vector_database_service import VectorDatabaseService
            vector_service = VectorDatabaseService()
            
            for key in keys_to_delete:
                try:
                    deleted_chunks = await vector_service.delete_document_chunks(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        document_key=key
                    )
                    total_deleted_chunks += deleted_chunks
                except Exception as e:
                    logger.warning(f"⚠️ VECTOR DB: Failed to delete chunks for document key '{key}': {e}")
            
            logger.info(f"🗑️ VECTOR DB: Deleted {total_deleted_chunks} total chunks from vector database")
        except Exception as e:
            logger.warning(f"⚠️ VECTOR DB: Failed to delete chunks from vector database: {e}")
            # Continue with database update even if vector deletion fails
        
        # Update database with remaining documents (or clear all if no persona filter)
        success = await db_adapter.update_research_documents_data(
            project_id, tenant_id, updated_research_data
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "delete_failed",
                    "message": "Failed to delete documents from database"
                }
            )
        
        # Log the deletion
        await security_service.log_project_access(
            user_id=user_id,
            project_id=project_id,
            operation='delete_all_documents',
            details={
                'deleted_documents': deleted_documents,
                'deleted_count': deleted_count
            }
        )
        
        logger.info(f"✅ DOCUMENTS DELETE: Successfully deleted {deleted_count} documents from project {project_id}")
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} document(s)",
            "deleted_documents": deleted_documents,
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ DOCUMENTS DELETE: Failed to delete all documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "delete_error",
                "message": f"Failed to delete documents: {str(e)}"
            }
        )


# ---------- Analysis Execution Endpoints ----------

@analysis_router.post("/projects/{project_id}/execute", response_model=AnalysisExecutionResponse)
async def execute_market_research_analysis(
    project_id: str,
    http_request: Request,
    request: Optional[AnalysisExecutionRequest] = None,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Start market research analysis for a VMP project.
    
    This endpoint initiates the analysis workflow that validates project
    assumptions against uploaded research data. Includes credit system
    integration and tenant validation.
    
    **Requirements**: 8.1, 8.4
    """
    try:
        # Get user info from current_user for credit checks
        auth_user_id = current_user.get("user_id")
        auth_tenant_id = current_user.get("tenant_id")
        plan_type = current_user.get("tenant_type", "individual")
        user_roles = current_user.get("roles", [])
        is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"
        
        # Credit check - resolve feature name to UUID
        from src.mint.api.features.dependencies import resolve_feature_id
        feature_id = await resolve_feature_id("Market Research Analysis")
        
        if not is_super_admin and auth_tenant_id and not credit_service.has_sufficient_credits_for_feature(
            tenant_id=auth_tenant_id,
            feature_id=feature_id,
            plan_type=plan_type,
        ):
            raise HTTPException(
                status_code=402,
                detail={"code": "insufficient_credits", "message": "You do not have enough credits for this feature."}
            )
        
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "project_not_found",
                    "message": f"VMP project {project_id} not found or inaccessible"
                }
            )
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        if not tenant_id or not user_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_project",

                    "message": "Project missing required tenant_id or user_id"
                }
            )
        
        logger.info(f"🔍 DEBUG: Auto-resolved from project {project_id}: tenant_id={tenant_id}, user_id={user_id}")
        logger.info("🚀 Enhanced processing, fact validation, and persona-aware routing are always enabled")
        
        # Validate tenant access and rate limiting
        await security_service.validate_tenant_access(user_id, tenant_id)
        await security_service.check_rate_limit(user_id, 'analysis_execution', http_request)
        
        # MULTI-PERSONA VALIDATION: Check if persona_id is required and valid
        from src.vpm.adapters.database_adapter import get_yuba_database_adapter
        vpm_db_adapter = get_yuba_database_adapter()
        project_personas = await vpm_db_adapter.get_project_personas(project_id)
        
        persona_id = request.persona_id if request else None
        logger.info(f"📋 ANALYSIS PERSONA CHECK: Project has {len(project_personas)} persona(s), requested persona: {persona_id}")
        
        # 🎭 PARALLEL EXECUTION: If project has multiple personas and no specific persona requested
        if len(project_personas) > 1:
            if not persona_id:
                # Option 1: Run all personas in parallel (NEW!)
                logger.info(f"🚀 PARALLEL ANALYSIS: Starting parallel analysis for {len(project_personas)} personas")
                
                import asyncio
                
                # Create analysis tasks for each persona
                analysis_tasks = []
                for persona in project_personas:
                    pid = persona.get("id")
                    task = analysis_service.analyze_market_research(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        persona_id=pid,
                        target_assumptions=request.target_assumptions if request else None
                    )
                    analysis_tasks.append((pid, task))
                
                # Execute all analyses in parallel
                results = await asyncio.gather(*[task for _, task in analysis_tasks], return_exceptions=True)
                
                # Process results
                successful_personas = []
                failed_personas = []
                
                for (pid, _), result in zip(analysis_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ PARALLEL: Analysis failed for persona '{pid}': {result}")
                        failed_personas.append({"persona_id": pid, "error": str(result)})
                    elif result.get("success"):
                        logger.info(f"✅ PARALLEL: Analysis completed for persona '{pid}'")
                        successful_personas.append(pid)
                    else:
                        logger.error(f"❌ PARALLEL: Analysis failed for persona '{pid}': {result.get('error')}")
                        failed_personas.append({"persona_id": pid, "error": result.get("error")})
                
                # Return combined results
                logger.info(f"🎭 PARALLEL COMPLETE: {len(successful_personas)} succeeded, {len(failed_personas)} failed")
                
                return AnalysisExecutionResponse(
                    success=len(successful_personas) > 0,
                    message=f"Parallel analysis completed for {len(successful_personas)}/{len(project_personas)} personas",
                    data={
                        "project_id": project_id,
                        "execution_mode": "parallel",
                        "total_personas": len(project_personas),
                        "successful_personas": successful_personas,
                        "failed_personas": failed_personas,
                        "status": "completed" if len(failed_personas) == 0 else "partial"
                    }
                )
            
            # Validate persona_id exists in project
            valid_persona_ids = [p.get("id") for p in project_personas]
            if persona_id not in valid_persona_ids:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' not found in project.",
                        "available_personas": [{"id": p.get("id"), "name": p.get("name")} for p in project_personas]
                    }
                )
            
            logger.info(f"✅ ANALYSIS PERSONA VALIDATION: Using persona '{persona_id}' for analysis")
        
        # If project has single persona, use it automatically
        elif len(project_personas) == 1:
            if not persona_id:
                persona_id = project_personas[0].get("id")
                logger.info(f"🔄 AUTO-ASSIGN: Single persona project, using persona '{persona_id}' for analysis")
            elif persona_id != project_personas[0].get("id"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "invalid_persona_id",
                        "message": f"Persona ID '{persona_id}' does not match project's persona '{project_personas[0].get('id')}'.",
                        "available_personas": [{"id": project_personas[0].get("id"), "name": project_personas[0].get("name")}]
                    }
                )
        
        # If no personas exist yet, this is an error
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_personas_found",
                    "message": "Project must have at least one persona before running analysis. Please complete persona identification first."
                }
            )
        
        # TODO: Integrate with credit system (deduct credits for analysis)
        # This would follow the same pattern as other VMP services
        # credit_cost = calculate_analysis_cost(project_assumptions_count)
        # await credit_service.deduct_credits(user_id, tenant_id, credit_cost)
        
        # Execute analysis using the service with persona_id
        result = await analysis_service.analyze_market_research(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            persona_id=persona_id,
            target_assumptions=request.target_assumptions if request else None
        )
        
        if not result["success"]:
            # Handle different error types
            error_code = result.get("error_code", "analysis_error")
            
            if error_code == "ACCESS_DENIED":
                raise HTTPException(status_code=403, detail=result["error"])
            elif error_code == "PROJECT_NOT_FOUND":
                raise HTTPException(status_code=404, detail=result["error"])
            elif error_code == "PROJECT_NOT_READY":
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "project_not_ready",
                        "message": result["error"],
                        "missing_requirements": result.get("missing_requirements", [])
                    }
                )
            elif error_code == "NO_RESEARCH_DATA":
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "no_research_data",
                        "message": result["error"]
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": error_code,
                        "message": result["error"]
                    }
                )
        
        # Calculate estimated completion time (rough estimate)
        assumptions_count = result["data"]["project_context"]["assumptions_count"]
        estimated_minutes = max(5, assumptions_count * 2)  # 2 minutes per assumption, minimum 5 minutes
        estimated_completion = datetime.utcnow() + timedelta(minutes=estimated_minutes)
        
        # Get persona name for response
        persona_name = None
        for p in project_personas:
            if p.get("id") == persona_id:
                persona_name = p.get("name")
                break
        
        # Log analysis execution for audit
        await security_service.log_project_access(
            user_id=user_id,
            project_id=project_id,
            operation='execute_analysis',
            details={
                'session_id': result["data"]["session_id"],
                'assumptions_count': assumptions_count,
                'target_assumptions': request.target_assumptions if request else None,
                'persona_id': persona_id,
                'persona_name': persona_name
            }
        )
        
        # Consume credits after successful analysis start
        if not is_super_admin and auth_tenant_id:
            try:
                request_id = str(uuid.uuid4())
                credit_service.consume_feature(
                    tenant_id=auth_tenant_id,
                    user_id=auth_user_id,
                    feature_id=feature_id,
                    plan_type=plan_type,
                    request_id=request_id,
                    reason="market_research_analysis_execution",
                    project_id=project_id,
                    metadata={"persona_id": persona_id, "assumptions_count": assumptions_count}
                )
            except Exception as credit_error:
                logger.warning(f"⚠️ Credit consumption failed (non-blocking): {credit_error}")
        
        return AnalysisExecutionResponse(
            success=True,
            message=f"Market research analysis started successfully for persona '{persona_name}'",
            data={
                "session_id": result["data"]["session_id"],
                "project_id": project_id,
                "persona_id": persona_id,
                "persona_name": persona_name,
                "status": result["data"]["status"],
                "started_at": result["data"]["analyzed_at"],
                "estimated_completion": estimated_completion.isoformat(),
                "progress": {
                    "total_assumptions": assumptions_count,
                    "processed_assumptions": 0,
                    "current_stage": "initializing"
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "execution_error",
                "message": f"Failed to start analysis: {str(e)}"
            }
        )


# ---------- Analysis Status and Results Endpoints ----------

@analysis_router.get("/projects/{project_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    project_id: str,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get analysis progress and status for a project.
    
    This endpoint provides real-time progress tracking including current
    stage, processed assumptions, and estimated completion time.
    
    **Requirements**: 8.5, 10.2
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(status_code=404, detail="Project not found")
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # Get analysis status and progress from context
        analysis_data = project_context.get("analysis_data", {})
        
        # Get status from the correct location (analysis_data.stage)
        stage = analysis_data.get("stage", "not_started")
        project_status = project_context.get("analysis_status", "not_started")
        
        # Map stage to status for API consistency
        if stage == "analysis_completed":
            status = "completed"
        elif stage in ["analyzing_assumptions", "processing"]:
            status = "processing"
        elif stage == "not_started":
            status = "not_started"
        else:
            status = project_status  # Fallback to project status
        
        logger.info(f"🔍 STATUS ENDPOINT DEBUG: stage='{stage}', project_status='{project_status}', mapped_status='{status}'")
        
        # Build response data
        response_data = {
            "project_id": project_id,
            "status": status,
            "stage": stage
        }
        
        # Add session info if analysis has been started
        if analysis_data and analysis_data.get("session_id"):
            session_metadata = analysis_data.get("session_metadata", {})
            response_data.update({
                "session_id": analysis_data["session_id"],
                "started_at": session_metadata.get("started_at"),
                "last_updated": session_metadata.get("updated_at", datetime.utcnow().isoformat())
            })
            
            # Add completion time if completed
            if status == "completed" or stage == "analysis_completed":
                response_data["completed_at"] = session_metadata.get("completed_at")
        
        # Add progress information if available
        if analysis_data.get("total_assumptions", 0) > 0:
            progress = AnalysisProgress(
                total_assumptions=analysis_data["total_assumptions"],
                processed_assumptions=analysis_data.get("processed_assumptions", 0),
                current_assumption=analysis_data.get("current_assumption"),
                current_stage=analysis_data.get("stage", "unknown"),
                percentage_complete=0  # Will be calculated by the model validator
            )
            response_data["progress"] = progress
            
            # Estimate completion time for in-progress analysis
            if status == "processing" and progress.processed_assumptions < progress.total_assumptions:
                remaining_assumptions = progress.total_assumptions - progress.processed_assumptions
                estimated_minutes = remaining_assumptions * 2  # 2 minutes per assumption
                estimated_completion = datetime.utcnow() + timedelta(minutes=estimated_minutes)
                response_data["estimated_completion"] = estimated_completion.isoformat()
        
        # Add error information if failed
        if status == "failed" and analysis_data and "error" in analysis_data:
            error_info = analysis_data["error"]
            response_data["error"] = AnalysisError(
                error_code=error_info.get("context", {}).get("error_code", "unknown_error"),
                message=error_info["message"],
                details=error_info.get("context", {}),
                occurred_at=error_info["occurred_at"]
            )
        
        return AnalysisStatusResponse(
            success=True,
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis status: {str(e)}"
        )


@analysis_router.get("/projects/{project_id}/results", response_model=AnalysisResultsResponse)
async def get_analysis_results(
    project_id: str,
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Get analysis results for a completed analysis.
    
    This endpoint returns the structured JSON report (new format) for completed analyses.
    Falls back to markdown report for backward compatibility.
    
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(status_code=404, detail="Project not found")
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # 🎭 MULTI-PERSONA: Get analysis data from context
        analysis_data = project_context.get("analysis_data", {})
        
        # Debug: Log what we retrieved from database
        logger.info(f"🔍 RESULTS DEBUG: Retrieved analysis_data from database:")
        logger.info(f"🔍 RESULTS DEBUG: - analysis_data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
        
        # 🎭 Check if this is multi-persona format
        if "personas" in analysis_data:
            logger.info(f"🎭 RESULTS DEBUG: Multi-persona format detected")
            logger.info(f"🎭 RESULTS DEBUG: - Personas available: {list(analysis_data.get('personas', {}).keys())}")
        
        if analysis_data:
            assumption_analyses = analysis_data.get("assumption_analyses", [])
            final_report = analysis_data.get("final_report", "")
            session_id = analysis_data.get("session_id", "")
            stage = analysis_data.get("stage", "")
            
            logger.info(f"🔍 RESULTS DEBUG: - assumption_analyses count: {len(assumption_analyses)}")
            logger.info(f"🔍 RESULTS DEBUG: - final_report length: {len(final_report)}")
            logger.info(f"🔍 RESULTS DEBUG: - session_id: {session_id}")
            logger.info(f"🔍 RESULTS DEBUG: - stage: {stage}")
            
            for i, analysis in enumerate(assumption_analyses):
                assumption_id = analysis.get("assumption_id", "unknown")
                validation_status = analysis.get("validation_status", "unknown")
                logger.info(f"🔍 RESULTS DEBUG: - Analysis {i+1}: {assumption_id} - {validation_status}")
        
        if not analysis_data:
            raise HTTPException(
                status_code=404,
                detail="No analysis results found for this project"
            )
        
        # Get status from analysis_data (where it's actually stored)
        status = analysis_data.get("stage", "not_started")
        analysis_status = project_context.get("analysis_status", "not_started")
        
        logger.info(f"🔍 STATUS DEBUG: analysis_data.stage = '{status}', project_context.analysis_status = '{analysis_status}'")
        
        # Check if analysis is completed (check both locations for compatibility)
        is_completed = (status == "analysis_completed" or 
                       analysis_status == "completed" or 
                       status == "completed")
        
        if not is_completed:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "analysis_not_completed",
                    "message": f"Analysis is not completed. Current status: {status} (analysis_status: {analysis_status})",
                    "current_status": status,
                    "analysis_status": analysis_status
                }
            )
        
        session_metadata = analysis_data.get("session_metadata", {})
        
        # 🎭 MULTI-PERSONA: Handle both single and multi-persona formats
        if "personas" in analysis_data:
            # Multi-persona format: return all personas' reports
            
            # 🎭 PERSONA NAME ENRICHMENT: Get persona names from project (like VPC does)
            from src.vpm.adapters.database_adapter import get_yuba_database_adapter
            vpm_db_adapter = get_yuba_database_adapter()
            project_personas = await vpm_db_adapter.get_project_personas(project_id)
            
            # Build mapping: persona_id (P1, P2) -> persona_name
            persona_name_map = {p.get("id"): p.get("name") for p in project_personas or []}
            logger.info(f"🎭 PERSONA NAME MAP: {persona_name_map}")
            
            personas_data = {}
            for persona_id, persona_analysis in analysis_data.get("personas", {}).items():
                # Get persona_name from mapping
                persona_name = persona_name_map.get(persona_id, persona_id)
                
                personas_data[persona_id] = {
                    "persona_name": persona_name,  # 🎭 NEW: Add persona_name to response
                    "structured_report": persona_analysis.get("structured_report"),
                    "final_report": persona_analysis.get("final_report", ""),
                    "session_id": persona_analysis.get("session_id"),
                    "stage": persona_analysis.get("stage"),
                    "assumption_analyses": persona_analysis.get("assumption_analyses", [])
                }
            
            logger.info(f"🎭 RESULTS: Returning multi-persona results for {len(personas_data)} persona(s) with names")
            
            response_data = {
                "project_id": project_id,
                "status": "completed",
                "report_available": True,
                "format": "multi_persona",
                "personas": personas_data,
                "root_stage": analysis_data.get("stage")
            }
        else:
            # Legacy single-persona format
            structured_report = analysis_data.get("structured_report")
            final_report = analysis_data.get("final_report", "")
            
            # Check if we have either format
            if not structured_report and not final_report:
                raise HTTPException(
                    status_code=404,
                    detail="Analysis report not available"
                )
            
            logger.info(f"🚀 RESULTS: structured_report present: {structured_report is not None}")
            logger.info(f"📄 RESULTS: final_report length: {len(final_report)}")
            
            # Build response data with structured report (preferred) or markdown fallback
            response_data = {
                "project_id": project_id,
                "session_id": analysis_data.get("session_id"),
                "status": "completed",
                "completed_at": session_metadata.get("completed_at"),
                "report_available": True,
                "structured_report": structured_report,  # 🚀 NEW: JSON format
                "final_report": final_report,  # Backward compatibility
                "report_format": "json" if structured_report else "markdown"
            }
        
        return AnalysisResultsResponse(
            success=True,
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis results: {str(e)}"
        )


@analysis_router.delete("/projects/{project_id}/analysis")
async def clear_analysis_data(
    project_id: str,
    clear_documents: bool = Query(False, description="Also clear uploaded research documents"),
    analysis_service: EnterpriseMarketResearchService = Depends(get_analysis_service),
    security_service: VMPSecurityService = Depends(get_security_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear analysis data and optionally research documents for a project.
    
    This endpoint allows users to reset analysis data and start fresh.
    Useful for re-running analysis with different parameters or documents.
    """
    try:
        # Auto-resolve tenant_id and user_id from project_id
        project_context = await analysis_service._get_project_context(project_id)
        if not project_context:
            raise HTTPException(status_code=404, detail="Project not found")
        
        tenant_id = project_context.get("tenant_id")
        user_id = project_context.get("user_id")
        
        # Validate tenant access
        await security_service.validate_tenant_access(user_id, tenant_id)
        
        # Clear analysis data using the database adapter
        db_adapter = analysis_service.db_adapter
        success = await db_adapter.clear_analysis_data(project_id, tenant_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear analysis data"
            )
        
        cleared_items = ["analysis_data", "analysis_status"]
        
        # Clear research documents if requested
        if clear_documents:
            doc_success = await db_adapter.clear_research_documents(project_id, tenant_id)
            if doc_success:
                cleared_items.append("research_documents")
        
        # Log clearing action for audit
        await security_service.log_project_access(
            user_id=user_id,
            project_id=project_id,
            operation='clear_analysis_data',
            details={
                'cleared_items': cleared_items,
                'clear_documents': clear_documents
            }
        )
        
        return {
            "success": True,
            "message": f"Successfully cleared {', '.join(cleared_items)}",
            "project_id": project_id,
            "cleared_items": cleared_items,
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear analysis data: {str(e)}"
        )


# ---------- Error Handlers ----------
# Note: Exception handlers are added to the main FastAPI app, not the router

# These error handlers would be added to the main app like this:
# @app.exception_handler(422)
# async def validation_exception_handler(request: Request, exc: HTTPException):
#     """Handle validation errors with detailed information"""
#     return JSONResponse(
#         status_code=422,
#         content={
#             "error": "validation_error",
#             "message": "Request validation failed",
#             "details": exc.detail
#         }
#     )
#
# @app.exception_handler(500)
# async def internal_server_error_handler(request: Request, exc: HTTPException):
#     """Handle internal server errors with logging"""
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": "internal_server_error",
#             "message": "An internal server error occurred",
#             "details": str(exc.detail) if hasattr(exc, 'detail') else "Unknown error"
#         }
#     )

# ---------- Router Debug Information ----------
logger.info("🔍 ROUTER DEBUG: Market Research Analysis router setup complete")
logger.info(f"🔍 ROUTER DEBUG: Final router has {len(analysis_router.routes)} total routes")

# Log all registered routes for debugging
for i, route in enumerate(analysis_router.routes):
    route_info = {
        'path': getattr(route, 'path', 'unknown'),
        'methods': getattr(route, 'methods', 'unknown'),
        'name': getattr(route, 'name', 'unknown')
    }
    logger.info(f"🔍 ROUTER DEBUG: Route {i+1}: {route_info['methods']} {route_info['path']} (name: {route_info['name']})")

logger.info("🔍 ROUTER DEBUG: Market Research Analysis router ready for inclusion")
