"""
Payment Management Module

This module provides comprehensive payment functionality for the MINT credit system,
including Stripe integration, payment processing, and credit allocation.

Components:
- endpoints: Payment API endpoints
- service: Payment processing service
- models: Payment data models
- stripe_service: Stripe integration service
"""

from .endpoints import router as payment_router
from .service import PaymentService, payment_service
from .models import (
    PaymentRequest, PaymentResponse, CreditPackage, 
    PaymentStatus, PaymentMethod, PaymentHistory
)
from .stripe_service import StripeService, stripe_service

# Public API
__all__ = [
    # Router
    "payment_router",
    
    # Services
    "PaymentService",
    "payment_service",
    "StripeService", 
    "stripe_service",
    
    # Models
    "PaymentRequest",
    "PaymentResponse", 
    "CreditPackage",
    "PaymentStatus",
    "PaymentMethod",
    "PaymentHistory"
]

# Module metadata
__version__ = "1.0.0"
