"""
Payment API Endpoints

This module provides REST API endpoints for payment functionality including:
1. Credit package listing
2. Payment creation and processing
3. Payment status checking
4. Payment history
5. Stripe webhook handling
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_user
from .service import payment_service
from .stripe_service import stripe_service
from .models import (
    PaymentRequest, PaymentResponse, CreditPackage, PaymentHistory,
    PaymentListResponse, CreditPackageListResponse, CreditType,
    PaymentWebhookEvent
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router for payment endpoints
router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("/packages", response_model=CreditPackageListResponse)
async def get_credit_packages(
    credit_type: Optional[CreditType] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CreditPackageListResponse:
    """
    Get available credit packages.
    
    Args:
        credit_type: Optional filter by credit type
        current_user: Authenticated user
        
    Returns:
        List of available credit packages
    """
    try:
        packages = await payment_service.get_credit_packages(credit_type)
        
        return CreditPackageListResponse(
            packages=packages,
            currency="USD"
        )
        
    except Exception as e:
        logger.error(f"Error getting credit packages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "packages_error",
                "message": "Failed to retrieve credit packages"
            }
        )


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_request: PaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PaymentResponse:
    """
    Create a new payment for credit purchase.
    
    Args:
        payment_request: Payment request details
        current_user: Authenticated user
        
    Returns:
        Payment response with payment details
    """
    try:
        user_id = current_user["user_id"]
        user_email = current_user.get("email")
        
        payment_response = await payment_service.create_payment(
            user_id=user_id,
            payment_request=payment_request,
            user_email=user_email
        )
        
        logger.info(f"Created payment {payment_response.payment_id} for user {user_id}")
        
        return payment_response
        
    except ValueError as e:
        logger.warning(f"Invalid payment request from user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_request",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "payment_error",
                "message": "Failed to create payment"
            }
        )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PaymentResponse:
    """
    Get payment status.
    
    Args:
        payment_id: Payment identifier
        current_user: Authenticated user
        
    Returns:
        Payment status response
    """
    try:
        user_id = current_user["user_id"]
        
        payment = await payment_service.get_payment_status(payment_id, user_id)
        
        if not payment:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "payment_not_found",
                    "message": "Payment not found"
                }
            )
        
        return payment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment status {payment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "payment_status_error",
                "message": "Failed to get payment status"
            }
        )


@router.get("/", response_model=PaymentListResponse)
async def get_payment_history(
    page: int = 1,
    per_page: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PaymentListResponse:
    """
    Get user's payment history.
    
    Args:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        current_user: Authenticated user
        
    Returns:
        Payment history response
    """
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        user_id = current_user["user_id"]
        
        payment_history = await payment_service.get_payment_history(
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        
        return payment_history
        
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "history_error",
                "message": "Failed to retrieve payment history"
            }
        )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhook events.
    
    Args:
        request: FastAPI request object
        stripe_signature: Stripe signature header
        
    Returns:
        Success response
    """
    try:
        if not stripe_signature:
            logger.warning("Stripe webhook received without signature")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Get raw body
        body = await request.body()
        
        # Handle webhook with Stripe service
        webhook_data = await stripe_service.handle_webhook(body, stripe_signature)
        
        if webhook_data:
            # Process payment completion if applicable
            if webhook_data["event_type"] in ["payment_succeeded", "payment_failed", "payment_canceled"]:
                success = await payment_service.process_payment_completion(
                    payment_id=webhook_data["payment_id"],
                    webhook_data=webhook_data
                )
                
                if not success:
                    logger.error(f"Failed to process payment completion: {webhook_data['payment_id']}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "webhook_error",
                "message": "Webhook processing failed"
            }
        )


@router.get("/methods/stripe")
async def get_stripe_payment_methods(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's saved Stripe payment methods.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of saved payment methods
    """
    try:
        user_id = current_user["user_id"]
        
        # This would require storing Stripe customer ID in user profile
        # For now, return empty list
        return {
            "payment_methods": [],
            "message": "Payment methods retrieval not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "payment_methods_error",
                "message": "Failed to retrieve payment methods"
            }
        )


# Health check endpoint
@router.get("/health")
async def payment_health():
    """Payment service health check."""
    return {
        "status": "healthy",
        "service": "payments",
        "timestamp": datetime.utcnow().isoformat(),
        "stripe_configured": bool(stripe_service.webhook_secret)
    }
