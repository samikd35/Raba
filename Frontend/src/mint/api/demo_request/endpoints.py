"""
Demo Request Endpoints

API endpoints for enterprise demo request functionality.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from .models import DemoRequest, DemoRequestResponse
from ..services.communication.email_service import email_service
from ..auth_v2.utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/demo-request",
    response_model=DemoRequestResponse,
    summary="Submit Enterprise Demo Request",
    description="Submit a demo request for enterprise customers. Sends notification email to the sales team at info@yubanow.com."
)
async def submit_demo_request(
    request: DemoRequest,
    current_user: dict = Depends(get_current_user),
) -> DemoRequestResponse:
    """
    Submit an enterprise demo request.
    
    This endpoint:
    1. Validates the demo request data
    2. Sends a notification email to info@yubanow.com
    3. Returns confirmation to the user
    
    Accessible to any authenticated user.
    """
    try:
        # Extract data from request
        data = request.demo_request
        
        # Generate request ID and timestamp
        request_id = str(uuid.uuid4())
        submitted_at = data.metadata.submitted_at if data.metadata and data.metadata.submitted_at else datetime.utcnow().isoformat() + "Z"
        
        # Get metadata with defaults
        metadata = data.metadata or {}
        requested_tier = metadata.requested_tier if hasattr(metadata, 'requested_tier') else "organization"
        source = metadata.source if hasattr(metadata, 'source') else "pricing_page"
        
        logger.info(f"📧 Processing demo request from {data.email} for organization: {data.organization.name}")
        
        # Send notification email to sales team
        email_sent = email_service.send_enterprise_demo_request_email(
            full_name=data.full_name,
            email=data.email,
            phone_number=data.phone_number,
            job_title=data.job_title,
            org_name=data.organization.name,
            org_type=data.organization.type,
            org_size=data.organization.size,
            country=data.organization.location.country,
            city=data.organization.location.city,
            expected_users=data.expected_users,
            additional_notes=data.additional_notes or "",
            requested_tier=requested_tier,
            source=source,
            submitted_at=submitted_at,
        )
        
        if email_sent:
            logger.info(f"✅ Demo request email sent successfully for request_id: {request_id}")
            return DemoRequestResponse(
                success=True,
                message="Your demo request has been submitted successfully. Our team will contact you shortly.",
                request_id=request_id,
                submitted_at=submitted_at,
            )
        else:
            logger.error(f"❌ Failed to send demo request email for {data.email}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process demo request. Please try again or contact us directly at info@yubanow.com"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing demo request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your demo request. Please try again or contact us directly at info@yubanow.com"
        )
