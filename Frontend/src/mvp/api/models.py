"""
API Models for MVP Module

Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from datetime import datetime


# ==================== BASE MODELS (SHARED) ====================

class PrimaryStatementModel(BaseModel):
    """Model for structured primary statement."""
    model_config = ConfigDict(populate_by_name=True)
    
    our: str = Field(..., description="Products or services offered")
    help: str = Field(..., description="Target customer segment")
    who_want_to: str = Field(..., description="Jobs to be done or customer goals")
    by: str = Field(..., description="Pain relievers - how we reduce/remove/avoid pains")
    and_: str = Field(..., alias="and", description="Gain creators - how we enable/increase gains")
    unlike: str = Field(..., description="Competitive differentiation")


# ==================== VPS REQUEST MODELS ====================

class VPSGenerationRequest(BaseModel):
    """Request for VPS generation."""
    creativity_level: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="AI creativity level (0.0 = conservative, 1.0 = creative)"
    )


class VPSUpdateRequest(BaseModel):
    """Request to update VPS (legacy single-persona format)."""
    primary_statement: Optional[PrimaryStatementModel] = Field(
        None,
        description="Updated structured primary value proposition statement"
    )
    extended_statement: Optional[str] = Field(
        None,
        min_length=150,
        max_length=2000,  # Increased from 1000 to 2000 to accommodate AI-generated content
        description="Updated extended statement with evidence"
    )
    key_differentiators: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Updated list of 3 key differentiators"
    )


class VPSEditRequest(BaseModel):
    """
    Request to edit VPS v1 (multi-persona support).
    
    Accepts EITHER:
    1. Direct array: [{persona1_vps}, {persona2_vps}]
    2. Wrapped format: {"vps_data": [{persona1_vps}, {persona2_vps}]}
    3. Full GET response: {"success": true, "vps_data": [...], ...}
    """
    model_config = ConfigDict(extra='ignore')  # Ignore extra fields from GET response
    
    # Direct array format
    vps_data: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of VPS objects (1-2 items, one per persona)"
    )
    
    # For accepting full GET response format
    success: Optional[bool] = Field(None, description="Ignored - from GET response")
    project_id: Optional[str] = Field(None, description="Ignored - from GET response")
    current_version: Optional[str] = Field(None, description="Ignored - from GET response")
    message: Optional[str] = Field(None, description="Ignored - from GET response")
    
    def get_vps_data(self) -> List[Dict[str, Any]]:
        """Extract VPS data from either format."""
        if self.vps_data is not None:
            return self.vps_data
        else:
            raise ValueError(
                "Must provide 'vps_data' array. "
                "You can copy-paste the entire GET response or send {\"vps_data\": [...]}."
            )


class VPSV2GenerationRequest(BaseModel):
    """Request for VPS v2 (refined) generation based on solution critique."""
    creativity_level: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="AI creativity level (0.0-1.0), affects temperature"
    )


# ==================== VPS RESPONSE MODELS ====================


class DifferentiatorModel(BaseModel):
    """Model for a key differentiator."""
    model_config = ConfigDict(extra='ignore')  # Allow extra fields like 'changed', 'change_reason' in v2
    
    id: str = Field(..., description="Unique identifier (e.g., 'diff-001')")
    title: str = Field(..., description="Differentiator title")
    description: str = Field(..., description="Detailed description with evidence")
    evidence_source: str = Field(
        ...,
        description="Source of evidence (field_research, vpc_analysis, assumption_validation, market_evidence, market_research_analysis)"
    )


class GenerationMetadataModel(BaseModel):
    """Model for generation metadata."""
    model_config = ConfigDict(extra='ignore')  # Allow extra fields like 'refined_from', 'critique_chunks_used' in v2
    
    generated_at: str = Field(..., description="ISO timestamp of generation")
    generated_by: Optional[str] = Field(None, description="User ID who generated")
    model_used: str = Field(..., description="AI model used (e.g., 'gpt-4o-mini')")
    context_sources: List[str] = Field(..., description="List of context sources used")
    evidence_count: int = Field(..., description="Number of evidence items used")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    context_completeness: float = Field(..., ge=0.0, le=1.0, description="Context completeness (0.0-1.0)")
    creativity_level: float = Field(..., ge=0.0, le=1.0, description="Creativity level used")
    version: str = Field(..., description="Version (v1 or v2)")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    last_updated_at: Optional[str] = Field(None, description="Last update timestamp")
    last_updated_by: Optional[str] = Field(None, description="Last update user ID")


class VPSDataModel(BaseModel):
    """Model for VPS data (supports multi-persona)."""
    model_config = ConfigDict(extra='ignore')  # Allow extra fields like 'refinement_metadata' in v2
    
    # Persona metadata (optional for backwards compatibility)
    persona_id: Optional[str] = Field(None, description="Persona ID this VPS is for")
    persona_name: Optional[str] = Field(None, description="Persona name this VPS is for")
    
    # VPS content
    primary_statement: PrimaryStatementModel = Field(..., description="Structured primary value proposition statement")
    extended_statement: str = Field(..., description="Extended statement with evidence")
    key_differentiators: List[DifferentiatorModel] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly 3 key differentiators"
    )
    generation_metadata: GenerationMetadataModel = Field(..., description="Generation metadata")


class VPSResponse(BaseModel):
    """Response with VPS data."""
    success: bool = Field(..., description="Whether operation was successful")
    data: Dict[str, Any] = Field(..., description="Response data")
    message: str = Field(..., description="Human-readable message")


class VPSDetailResponse(BaseModel):
    """Detailed VPS response (supports multi-persona array)."""
    success: bool = Field(..., description="Whether operation was successful")
    vps_data: Optional[List[VPSDataModel]] = Field(None, description="VPS data array (1-2 items per persona)")
    project_id: str = Field(..., description="Project ID")
    current_version: str = Field(..., description="Current VPS version (v1, v2, or none)")
    message: str = Field(..., description="Human-readable message")


# ==================== COMMON MODELS ====================

class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    message: str = Field(..., description="Human-readable error message")


class VersionInfoModel(BaseModel):
    """Model for version information."""
    vps: str = Field(..., description="Current VPS version (v1, v2, or none)")
    vps_updated_at: Optional[str] = Field(None, description="Last VPS update timestamp")
    bmc: Optional[str] = Field(None, description="Current BMC version (future)")
    bmc_updated_at: Optional[str] = Field(None, description="Last BMC update timestamp (future)")


class ProjectVersionsResponse(BaseModel):
    """Response with project version information."""
    success: bool = Field(..., description="Whether operation was successful")
    project_id: str = Field(..., description="Project ID")
    versions: VersionInfoModel = Field(..., description="Version information")
    message: str = Field(..., description="Human-readable message")


# ==================== VALIDATION HELPERS ====================

def validate_differentiators(differentiators: List[Dict[str, Any]]) -> bool:
    """
    Validate differentiators structure.
    
    Args:
        differentiators: List of differentiator dictionaries
        
    Returns:
        True if valid, False otherwise
    """
    if len(differentiators) != 3:
        return False
    
    required_fields = ['title', 'description', 'evidence_source']
    valid_sources = ['field_research', 'vpc_analysis', 'assumption_validation', 'market_evidence']
    
    for diff in differentiators:
        # Check required fields
        if not all(field in diff for field in required_fields):
            return False
        
        # Check evidence source
        if diff['evidence_source'] not in valid_sources:
            return False
        
        # Check field types
        if not isinstance(diff['title'], str) or not isinstance(diff['description'], str):
            return False
    
    return True


# ==================== BMC REQUEST MODELS ====================

class BMCGenerationRequest(BaseModel):
    """Request for BMC generation."""
    creativity_level: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="AI creativity level (0.0 = conservative, 1.0 = creative)"
    )


class BMCBlockUpdateRequest(BaseModel):
    """Request to update a specific BMC block."""
    block_data: Dict[str, Any] = Field(
        ...,
        description="Updated block data"
    )


class BMCBlockRegenerateRequest(BaseModel):
    """Request to regenerate a specific BMC block."""
    creativity_level: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="AI creativity level for regeneration"
    )


class BMCItemAddRequest(BaseModel):
    """Request to add a new item to a BMC block with AI enhancement."""
    block_name: str = Field(
        ...,
        description="Name of the BMC block to add item to (e.g., 'customer_segments', 'value_propositions')"
    )
    label: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Label/name for the new item"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="User's description of the item (will be AI-enhanced)"
    )


class BMCItemAddResponse(BaseModel):
    """Response for BMC item addition with AI enhancement."""
    success: bool = Field(True, description="Operation success status")
    project_id: str = Field(..., description="VMP project ID")
    project_name: Optional[str] = Field(None, description="Project name")
    block_name: str = Field(..., description="Name of the block where item was added")
    added_item: Dict[str, Any] = Field(..., description="The newly added item with AI-enhanced description")
    ai_enhanced: bool = Field(True, description="Whether AI enhancement was applied")
    bmc: Optional[Dict[str, Any]] = Field(None, description="Updated complete BMC data")
    message: str = Field(..., description="Response message")


class BMCItemDeleteRequest(BaseModel):
    """Request to delete an item from a BMC block."""
    block_name: str = Field(
        ...,
        description="Name of the BMC block to delete item from (e.g., 'customer_segments', 'value_propositions')"
    )
    item_id: str = Field(
        ...,
        description="ID of the item to delete (e.g., 'ch-001', 'seg-002')"
    )


class BMCItemDeleteResponse(BaseModel):
    """Response for BMC item deletion."""
    success: bool = Field(True, description="Operation success status")
    project_id: str = Field(..., description="VMP project ID")
    project_name: Optional[str] = Field(None, description="Project name")
    block_name: str = Field(..., description="Name of the block where item was deleted")
    deleted_item_id: str = Field(..., description="ID of the deleted item")
    bmc: Optional[Dict[str, Any]] = Field(None, description="Updated complete BMC data")
    message: str = Field(..., description="Response message")


# ==================== BMC RESPONSE MODELS ====================

class BMCResponse(BaseModel):
    """Response for BMC operations."""
    success: bool = Field(True, description="Operation success status")
    project_id: str = Field(..., description="VMP project ID")
    project_name: Optional[str] = Field(None, description="Project name")
    bmc: Optional[Dict[str, Any]] = Field(None, description="Complete BMC data")
    message: str = Field(..., description="Response message")
    updated_block: Optional[str] = Field(None, description="Name of updated block (for update operations)")
    regenerated_block: Optional[str] = Field(None, description="Name of regenerated block (for regenerate operations)")
