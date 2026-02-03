"""
Pydantic models for API responses
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class CritiqueGenerateRequest(BaseModel):
    """Request to generate solution critique"""
    force_regenerate: bool = Field(
        default=True,
        description="Force regeneration even if critique exists"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "force_regenerate": True
            }
        }


class CritiqueGenerateResponse(BaseModel):
    """Response for critique generation request (async processing)"""
    success: bool
    session_id: str
    status: str  # processing | completed | failed
    message: str
    estimated_completion_seconds: int = Field(
        default=60,
        description="Estimated time to complete processing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Solution critique generation started",
                "estimated_completion_seconds": 60
            }
        }


class ProgressInfo(BaseModel):
    """Progress information for status endpoint"""
    current_step: str
    steps_completed: int
    total_steps: int


class CritiqueStatusResponse(BaseModel):
    """Response for critique status check"""
    success: bool
    status: str  # processing | completed | failed
    session_id: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[ProgressInfo] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status": "completed",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "started_at": "2024-01-20T10:30:00Z",
                "completed_at": "2024-01-20T10:31:15Z",
                "progress": {
                    "current_step": "synthesize_report",
                    "steps_completed": 9,
                    "total_steps": 9
                }
            }
        }


class CritiqueMetadata(BaseModel):
    """Metadata for critique results"""
    generated_at: str
    total_sources: int
    total_citations: int
    ai_model: str
    processing_time_seconds: Optional[int] = None


class CritiqueResultsResponse(BaseModel):
    """Response for critique results"""
    success: bool
    data: Dict[str, Any]  # Complete critique report JSON
    metadata: CritiqueMetadata
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "executive_summary": {
                        "overall_viability": "moderate_risk",
                        "total_critiques": 12,
                        "severity_distribution": {
                            "high": 5,
                            "medium": 4,
                            "low": 3
                        },
                        "top_3_risks": [
                            "Unvalidated customer demand [1][2]",
                            "Complex regulatory environment [5][6]",
                            "Unclear path to profitability [8][9]"
                        ]
                    },
                    "critiques_by_dimension": {},
                    "sources": []
                },
                "metadata": {
                    "generated_at": "2024-01-20T10:30:00Z",
                    "total_sources": 45,
                    "total_citations": 127,
                    "ai_model": "gpt-4.1",
                    "processing_time_seconds": 58
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "missing_required_data",
                "message": "BMC must be completed before generating solution critique",
                "details": {
                    "missing": ["bmc"]
                }
            }
        }
