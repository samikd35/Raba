"""
API Models for Data Analysis Agent

Request and response models for market research analysis endpoints.
Follows VMP API patterns for consistency.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from fastapi import UploadFile


# Request Models

class FileUploadRequest(BaseModel):
    """Request model for file upload endpoint"""
    project_id: str = Field(..., description="VMP project ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_123",
                "tenant_id": "tenant_456",
                "user_id": "user_789"
            }
        }


class AnalysisExecutionRequest(BaseModel):
    """Request model for analysis execution endpoint (project_id is now a path parameter)"""
    persona_id: Optional[str] = Field(
        None,
        description="Persona ID for multi-persona projects. Required if project has multiple personas. Analysis will use persona-specific VPC, hypothesis, and assumptions."
    )
    target_assumptions: Optional[List[str]] = Field(
        None, 
        description="Optional list of specific assumption IDs to analyze. If not provided, all assumptions from field_prep_data will be analyzed."
    )
    force_reprocess: Optional[bool] = Field(
        True,
        description="Force reprocessing of existing research documents"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "persona_id": "P1",
                "target_assumptions": None,
                "force_reprocess": True
                # Enhanced processing, fact validation, and persona-aware routing are always enabled
            }
        }


# Response Models

class FileUploadResponse(BaseModel):
    """Response model for file upload endpoint"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Files uploaded and processed successfully",
                "data": {
                    "project_id": "proj_123",
                    "uploaded_files": ["interview.pdf", "survey.csv"],
                    "processing_status": {
                        "pdf": {"status": "completed", "chunks": 45},
                        "csv": {"status": "completed", "chunks": 23}
                    },
                    "total_chunks": 68,
                    "uploaded_at": "2025-01-01T12:00:00Z"
                }
            }
        }


class AnalysisExecutionResponse(BaseModel):
    """Response model for analysis execution endpoint"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Market research analysis started successfully",
                "data": {
                    "session_id": "session_abc123",
                    "project_id": "proj_123",
                    "status": "processing",
                    "started_at": "2025-01-01T12:00:00Z",
                    "estimated_completion": "2025-01-01T12:15:00Z",
                    "progress": {
                        "total_assumptions": 5,
                        "processed_assumptions": 0,
                        "current_stage": "initializing"
                    }
                }
            }
        }


class AnalysisStatusResponse(BaseModel):
    """Response model for analysis status endpoint"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "project_id": "proj_123",
                    "session_id": "session_abc123",
                    "status": "processing",
                    "stage": "analyzing_assumptions",
                    "progress": {
                        "total_assumptions": 5,
                        "processed_assumptions": 2,
                        "current_assumption": "assumption-003",
                        "percentage_complete": 40
                    },
                    "started_at": "2025-01-01T12:00:00Z",
                    "estimated_completion": "2025-01-01T12:15:00Z",
                    "last_updated": "2025-01-01T12:08:00Z"
                }
            }
        }


class AnalysisResultsResponse(BaseModel):
    """Response model for analysis results endpoint"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "project_id": "proj_123",
                    "session_id": "session_abc123",
                    "status": "completed",
                    "completed_at": "2025-01-01T12:15:00Z",
                    "analysis_summary": {
                        "total_assumptions": 5,
                        "validated_assumptions": 3,
                        "partially_validated_assumptions": 1,
                        "invalidated_assumptions": 1,
                        "overall_confidence": 0.75
                    },
                    "report_available": True,
                    "report_format": "markdown"
                }
            }
        }


class DocumentProcessingStatus(BaseModel):
    """Model for document processing status"""
    status: Literal["processing", "completed", "failed"]
    chunks: Optional[int] = None
    error_message: Optional[str] = None
    updated_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "completed",
                "chunks": 45,
                "updated_at": "2025-01-01T12:05:00Z"
            }
        }


class AnalysisProgress(BaseModel):
    """Model for analysis progress tracking"""
    total_assumptions: int
    processed_assumptions: int
    current_assumption: Optional[str] = None
    percentage_complete: float
    current_stage: str
    
    @field_validator('percentage_complete', mode='before')
    @classmethod
    def calculate_percentage(cls, v, info):
        if info.data and 'total_assumptions' in info.data and info.data['total_assumptions'] > 0:
            processed = info.data.get('processed_assumptions', 0)
            return round((processed / info.data['total_assumptions']) * 100, 1)
        return 0.0
    
    class Config:
        schema_extra = {
            "example": {
                "total_assumptions": 5,
                "processed_assumptions": 2,
                "current_assumption": "assumption-003",
                "percentage_complete": 40.0,
                "current_stage": "analyzing_assumptions"
            }
        }


class AssumptionAnalysisSummary(BaseModel):
    """Model for assumption analysis summary"""
    assumption_id: str
    assumption_text: str
    validation_status: Literal["validated", "partially_validated", "invalidated"]
    confidence_score: float
    key_findings: List[str]
    analyzed_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "assumption_id": "assumption-001",
                "assumption_text": "Small business owners struggle with manual inventory tracking",
                "validation_status": "validated",
                "confidence_score": 0.85,
                "key_findings": [
                    "67% of surveyed businesses use manual tracking methods",
                    "Average 4 hours per week spent on inventory management",
                    "High correlation with reported pain points"
                ],
                "analyzed_at": "2025-01-01T12:10:00Z"
            }
        }


class AnalysisSessionInfo(BaseModel):
    """Model for analysis session information"""
    session_id: str
    project_id: str
    status: Literal["not_started", "processing", "completed", "failed"]
    stage: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_updated: str
    progress: Optional[AnalysisProgress] = None
    error: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "project_id": "proj_123",
                "status": "processing",
                "stage": "analyzing_assumptions",
                "started_at": "2025-01-01T12:00:00Z",
                "last_updated": "2025-01-01T12:08:00Z",
                "progress": {
                    "total_assumptions": 5,
                    "processed_assumptions": 2,
                    "current_assumption": "assumption-003",
                    "percentage_complete": 40.0,
                    "current_stage": "analyzing_assumptions"
                }
            }
        }


# Error Models

class AnalysisError(BaseModel):
    """Model for analysis error information"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    occurred_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "DOCUMENT_PROCESSING_ERROR",
                "message": "Failed to parse PDF file: corrupted document",
                "details": {
                    "filename": "interview.pdf",
                    "file_size": 2048576,
                    "error_type": "parsing_error"
                },
                "occurred_at": "2025-01-01T12:05:00Z"
            }
        }


class ValidationError(BaseModel):
    """Model for validation error information"""
    field: str
    message: str
    value: Optional[Any] = None
    
    class Config:
        schema_extra = {
            "example": {
                "field": "project_id",
                "message": "Project ID is required",
                "value": None
            }
        }


# Utility Models

class FileInfo(BaseModel):
    """Model for uploaded file information"""
    filename: str
    file_type: str
    file_size: int
    content_type: str
    uploaded_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "interview_transcript.pdf",
                "file_type": "pdf",
                "file_size": 2048576,
                "content_type": "application/pdf",
                "uploaded_at": "2025-01-01T12:00:00Z"
            }
        }


class ResearchDocumentInfo(BaseModel):
    """Model for research document information"""
    document_type: Literal["pdf", "csv"]
    filename: str
    file_size: int
    chunks_count: int
    processing_status: DocumentProcessingStatus
    persona_id: Optional[str] = Field(None, description="Persona ID this document is associated with (for multi-persona projects)")
    metadata: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "document_type": "pdf",
                "filename": "interview_transcript.pdf",
                "file_size": 2048576,
                "chunks_count": 45,
                "processing_status": {
                    "status": "completed",
                    "chunks": 45,
                    "updated_at": "2025-01-01T12:05:00Z"
                },
                "persona_id": "P1",
                "metadata": {
                    "pages": 12,
                    "extracted_text_length": 15000,
                    "language": "en",
                    "persona_id": "P1"
                }
            }
        }


class DocumentDeleteResponse(BaseModel):
    """Response model for individual document deletion"""
    success: bool
    message: str
    deleted_document: Dict[str, Any]
    remaining_documents: int
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Document 'interview_transcript.pdf' successfully deleted",
                "deleted_document": {
                    "filename": "interview_transcript.pdf",
                    "document_type": "pdf",
                    "file_size": 2048576,
                    "upload_timestamp": "2025-01-01T12:00:00Z"
                },
                "remaining_documents": 3
            }
        }


class BulkDocumentDeleteResponse(BaseModel):
    """Response model for bulk document deletion"""
    success: bool
    message: str
    deleted_documents: List[Dict[str, Any]]
    deleted_count: int
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully deleted 4 document(s)",
                "deleted_documents": [
                    {
                        "filename": "interview_transcript.pdf",
                        "document_type": "pdf",
                        "file_size": 2048576
                    },
                    {
                        "filename": "survey_data.csv",
                        "document_type": "csv",
                        "file_size": 1024000
                    }
                ],
                "deleted_count": 4
            }
        }