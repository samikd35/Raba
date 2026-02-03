"""
FastAPI Endpoints for Pitch Deck Generator

Provides endpoints to:
- Trigger deck generation (async)
- Get generated deck
- List deck versions
- Get generation status
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.mint.api.auth_v2.utils import get_current_user


# ============================================================================
# PLACEHOLDER DETECTION UTILITIES
# ============================================================================

# Common placeholder values that indicate user didn't provide real data
PLACEHOLDER_STRINGS = {
    "string", "str", "text", "example", "placeholder", "todo", "tbd",
    "n/a", "na", "none", "null", "undefined", "", "your_value_here",
    "enter_value", "fill_in", "xxx", "abc", "test"
}

def is_placeholder_value(value: Any) -> bool:
    """Check if a value is a placeholder that should be treated as missing."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower().strip() in PLACEHOLDER_STRINGS or not value.strip()
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, list):
        return len(value) == 0 or all(is_placeholder_value(v) for v in value)
    if isinstance(value, dict):
        return len(value) == 0 or all(is_placeholder_value(v) for v in value.values())
    return False

def clean_user_hints(hints: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove placeholder values from user hints.
    
    This ensures that placeholder data like "string" or 0 doesn't get passed
    to the workflow as real data.
    """
    cleaned = {}
    
    for key, value in hints.items():
        if key in ("deck_purpose", "stage", "category"):
            # Always keep these as they're enums
            cleaned[key] = value
            continue
        
        if isinstance(value, dict):
            # Recursively clean nested dicts
            cleaned_dict = {}
            for k, v in value.items():
                if not is_placeholder_value(v):
                    cleaned_dict[k] = v
            if cleaned_dict:  # Only add if there's real data
                cleaned[key] = cleaned_dict
        elif isinstance(value, list):
            # Clean lists (e.g., team_info)
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_item = {k: v for k, v in item.items() if not is_placeholder_value(v)}
                    if cleaned_item and len(cleaned_item) > 0:
                        # Only include items with at least one real value
                        has_real_value = any(not is_placeholder_value(v) for v in cleaned_item.values())
                        if has_real_value:
                            cleaned_list.append(cleaned_item)
                elif not is_placeholder_value(item):
                    cleaned_list.append(item)
            if cleaned_list:
                cleaned[key] = cleaned_list
        elif not is_placeholder_value(value):
            cleaned[key] = value
    
    return cleaned

from ..models import (
    GenerateDeckRequest,
    GenerateDeckResponse,
    DeckPackageResponse,
    DeckVersionListResponse,
    DeckVersionSummary,
    DeckStatusResponse,
    SlideContent,
    Placeholder,
)
from ..adapters.database_adapter import PitchDeckDatabaseAdapter
from ..workflow.pitch_workflow import run_pitch_deck_generation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mav/projects", tags=["Pitch Deck Generator"])


# ============================================================================
# BACKGROUND TASK
# ============================================================================

async def _generate_deck_background(
    project_id: str,
    tenant_id: str,
    user_id: str,
    user_hints: dict
):
    """Background task for deck generation."""
    try:
        logger.info(f"🚀 PITCH API: Starting background generation for project {project_id}")
        
        # Update status to processing
        db_adapter = PitchDeckDatabaseAdapter()
        await db_adapter.update_pitch_deck_status(project_id, tenant_id, "processing")
        
        # Run generation
        result = await run_pitch_deck_generation(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_hints=user_hints
        )
        
        if result.get("generation_status") == "completed":
            logger.info(f"✅ PITCH API: Generation completed for project {project_id}")
        else:
            logger.error(f"❌ PITCH API: Generation failed for project {project_id}: {result.get('error_message')}")
            await db_adapter.update_pitch_deck_status(
                project_id, tenant_id, "failed", result.get("error_message")
            )
            
    except Exception as e:
        logger.error(f"❌ PITCH API: Background generation error: {e}")
        try:
            db_adapter = PitchDeckDatabaseAdapter()
            await db_adapter.update_pitch_deck_status(project_id, tenant_id, "failed", str(e))
        except:
            pass


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/{project_id}/pitch-deck/generate",
    response_model=GenerateDeckResponse,
    summary="Generate Pitch Deck",
    description="Trigger pitch deck generation for a project. Runs asynchronously."
)
async def generate_pitch_deck(
    project_id: str,
    request: GenerateDeckRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger pitch deck generation.
    
    The generation runs asynchronously. Use the status endpoint to check progress.
    """
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    # Verify project access
    db_adapter = PitchDeckDatabaseAdapter()
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get next version number
    next_version = await db_adapter.get_next_version(project_id, tenant_id)
    
    # Build user hints from request
    user_hints = {}
    if request.deck_purpose:
        user_hints["deck_purpose"] = request.deck_purpose.value
    if request.stage:
        user_hints["stage"] = request.stage.value
    if request.category:
        user_hints["category"] = request.category.value
    if request.team_info:
        user_hints["team_info"] = [t.dict() for t in request.team_info]
    if request.financial_inputs:
        user_hints["financial_inputs"] = request.financial_inputs.dict()
    if request.traction_metrics:
        user_hints["traction_metrics"] = request.traction_metrics.dict()
    if request.target_investor_type:
        user_hints["target_investor_type"] = request.target_investor_type
    if request.geography:
        user_hints["geography"] = request.geography
    if request.sector:
        user_hints["sector"] = request.sector
    
    # Clean user hints - remove placeholder values like "string", 0, etc.
    # This ensures the workflow treats them as missing data needing placeholders
    original_hint_count = len(user_hints)
    user_hints = clean_user_hints(user_hints)
    logger.info(f"📋 PITCH API: Cleaned user hints - {original_hint_count} -> {len(user_hints)} fields (removed placeholders)")
    
    # Update status and start background task
    await db_adapter.update_pitch_deck_status(project_id, tenant_id, "processing")
    
    background_tasks.add_task(
        _generate_deck_background,
        project_id,
        tenant_id,
        user_id,
        user_hints
    )
    
    logger.info(f"🚀 PITCH API: Triggered generation for project {project_id}, version {next_version}")
    
    return GenerateDeckResponse(
        deck_id=project_id,
        version=next_version,
        status="processing",
        message=f"Pitch deck generation started. Version {next_version} will be created."
    )


@router.get(
    "/{project_id}/pitch-deck",
    response_model=DeckPackageResponse,
    summary="Get Pitch Deck",
    description="Get the latest or a specific version of the pitch deck."
)
async def get_pitch_deck(
    project_id: str,
    version: Optional[int] = Query(None, description="Specific version number, or latest if not provided"),
    current_user: dict = Depends(get_current_user)
):
    """Get pitch deck content."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = PitchDeckDatabaseAdapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get deck version
    deck = await db_adapter.get_deck_version(project_id, tenant_id, version)
    
    if not deck:
        raise HTTPException(
            status_code=404,
            detail="No pitch deck found. Generate one first."
        )
    
    # Convert slides to response model
    slides = []
    for s in deck.get("slides", []):
        slides.append(SlideContent(
            slide_type=s.get("slide_type", ""),
            slide_title=s.get("slide_title", ""),
            slide_bullets=s.get("slide_bullets", []),
            description=s.get("description", ""),
            citations_used=s.get("citations_used", []),
            placeholders=[Placeholder(**p) for p in s.get("placeholders", [])],
            warnings=s.get("warnings", [])
        ))
    
    return DeckPackageResponse(
        project_id=project_id,
        version=deck.get("version", 1),
        deck_purpose=deck.get("deck_purpose", ""),
        stage=deck.get("stage", ""),
        category=deck.get("category", ""),
        slides=slides,
        citations=deck.get("citations", []),
        warnings=deck.get("warnings", []),
        user_inputs=deck.get("user_inputs", {}),
        created_at=deck.get("created_at", ""),
        created_by=deck.get("created_by"),
        run_trace=deck.get("run_trace")
    )


@router.get(
    "/{project_id}/pitch-deck/versions",
    response_model=DeckVersionListResponse,
    summary="List Pitch Deck Versions",
    description="List all pitch deck versions for a project."
)
async def list_pitch_deck_versions(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all deck versions."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = PitchDeckDatabaseAdapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get versions
    versions = await db_adapter.list_deck_versions(project_id, tenant_id)
    deck_data = await db_adapter.get_pitch_deck_data(project_id, tenant_id)
    
    return DeckVersionListResponse(
        project_id=project_id,
        current_version=deck_data.get("current_version", 0),
        versions=[DeckVersionSummary(**v) for v in versions],
        total_count=len(versions)
    )


@router.get(
    "/{project_id}/pitch-deck/status",
    response_model=DeckStatusResponse,
    summary="Get Generation Status",
    description="Get the current status of pitch deck generation."
)
async def get_pitch_deck_status(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get deck generation status."""
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = PitchDeckDatabaseAdapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get project to check status
    project = await db_adapter.load_project_context(project_id, tenant_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    status = project.get("pitch_deck_status", "not_started")
    deck_data = project.get("pitch_deck_data", {})
    current_version = deck_data.get("current_version", 0)
    
    # Get progress info if processing
    progress = None
    if status == "processing":
        progress = {"message": "Generating pitch deck..."}
    
    # Build message
    if status == "not_started":
        message = "No pitch deck has been generated yet."
    elif status == "processing":
        message = "Pitch deck generation is in progress."
    elif status == "completed":
        message = f"Pitch deck generation completed. Latest version: {current_version}"
    else:
        message = "Pitch deck generation failed."
    
    return DeckStatusResponse(
        project_id=project_id,
        version=current_version,
        status=status,
        message=message,
        progress=progress
    )


@router.get(
    "/{project_id}/pitch-deck/preview",
    summary="Preview Deck Plan",
    description="Get a preview of the deck plan (slide types only, no content)."
)
async def preview_pitch_deck_plan(
    project_id: str,
    deck_purpose: Optional[str] = Query(None, description="FUNDRAISING, PARTNER_SALES, or DEMO"),
    stage: Optional[str] = Query(None, description="IDEATION, PRE_SEED, SEED, or GROWTH"),
    category: Optional[str] = Query(None, description="PLATFORM_SAAS, CPG, INFRA_PROJECT, or OTHER"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a preview of what the deck plan would look like.
    
    This is a lightweight endpoint that returns just the slide types
    without generating full content.
    """
    tenant_id = current_user.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    db_adapter = PitchDeckDatabaseAdapter()
    
    # Verify access
    has_access = await db_adapter.verify_project_access(project_id, tenant_id)
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Get project summary
    summary = await db_adapter.get_project_summary(project_id, tenant_id)
    
    # Default slide plan based on purpose/stage
    purpose = deck_purpose or "FUNDRAISING"
    stg = stage or "PRE_SEED"
    cat = category or "OTHER"
    
    # Build a basic slide plan
    must_have_slides = [
        {"slide_type": "Title", "priority": "MUST_HAVE"},
        {"slide_type": "Problem", "priority": "MUST_HAVE"},
        {"slide_type": "Solution", "priority": "MUST_HAVE"},
        {"slide_type": "Product", "priority": "MUST_HAVE"},
        {"slide_type": "BusinessModel", "priority": "MUST_HAVE"},
        {"slide_type": "Team", "priority": "MUST_HAVE"},
    ]
    
    # Add purpose-specific slides
    if purpose == "FUNDRAISING":
        must_have_slides.extend([
            {"slide_type": "Market", "priority": "MUST_HAVE", "web_allowed": True},
            {"slide_type": "Competition", "priority": "CONDITIONAL", "web_allowed": True},
            {"slide_type": "GTM", "priority": "MUST_HAVE"},
            {"slide_type": "Financials", "priority": "MUST_HAVE"},
            {"slide_type": "Ask", "priority": "MUST_HAVE"},
        ])
    elif purpose == "PARTNER_SALES":
        must_have_slides.extend([
            {"slide_type": "Market", "priority": "CONDITIONAL", "web_allowed": True},
            {"slide_type": "GTM", "priority": "MUST_HAVE"},
            {"slide_type": "Roadmap", "priority": "CONDITIONAL"},
        ])
    else:  # DEMO
        must_have_slides.extend([
            {"slide_type": "Validation", "priority": "CONDITIONAL"},
            {"slide_type": "Roadmap", "priority": "CONDITIONAL"},
        ])
    
    # Add traction/validation if available
    if summary.get("has_market_research"):
        must_have_slides.append({"slide_type": "Validation", "priority": "CONDITIONAL"})
    
    return {
        "project_id": project_id,
        "deck_purpose": purpose,
        "stage": stg,
        "category": cat,
        "available_artifacts": summary.get("available_artifacts", []),
        "slides_preview": must_have_slides,
        "estimated_slides": len(must_have_slides),
        "warnings": []
    }
