"""
Payment Service

This service handles payment operations including:
1. Credit package management
2. Payment processing coordination
3. Credit allocation after successful payment
4. Payment history tracking
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from ..system.core.supabase_client import get_service_role_client
from ..credit.credit_service import credit_service
from ..credit_audit.service import get_credit_audit_service
from .models import (
    CreditPackage, PaymentRequest, PaymentResponse, PaymentHistory,
    PaymentStatus, PaymentMethod, CreditType, PaymentListResponse
)
from .stripe_service import stripe_service

# Configure logging
logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling payment operations and credit allocation."""
    
    def __init__(self):
        """Initialize payment service."""
        self.supabase_client = get_service_role_client()
        self.credit_service = credit_service
        self.audit_service = get_credit_audit_service(self.supabase_client)
        
        # Define available credit packages
        self.credit_packages = {
            "credits_10": CreditPackage(
                id="credits_10",
                name="Starter Pack",
                credits=10,
                price=Decimal("9.99"),
                credit_type=CreditType.GENERAL,
                description="Perfect for getting started"
            ),
            "credits_25": CreditPackage(
                id="credits_25",
                name="Basic Pack",
                credits=25,
                price=Decimal("19.99"),
                credit_type=CreditType.GENERAL,
                bonus_credits=5,
                description="Great value for regular users"
            ),
            "credits_50": CreditPackage(
                id="credits_50",
                name="Popular Pack",
                credits=50,
                price=Decimal("34.99"),
                credit_type=CreditType.GENERAL,
                popular=True,
                bonus_credits=10,
                description="Most popular choice"
            ),
            "credits_100": CreditPackage(
                id="credits_100",
                name="Pro Pack",
                credits=100,
                price=Decimal("59.99"),
                credit_type=CreditType.GENERAL,
                bonus_credits=25,
                description="For power users"
            ),
            "pg_credits_5": CreditPackage(
                id="pg_credits_5",
                name="Problem Generator - Starter",
                credits=5,
                price=Decimal("14.99"),
                credit_type=CreditType.PROBLEM_GENERATOR,
                description="Problem generator credits for beginners"
            ),
            "pg_credits_15": CreditPackage(
                id="pg_credits_15",
                name="Problem Generator - Pro",
                credits=15,
                price=Decimal("39.99"),
                credit_type=CreditType.PROBLEM_GENERATOR,
                popular=True,
                bonus_credits=5,
                description="Best value for problem generation"
            )
        }
        
        logger.info("PaymentService initialized with credit packages")
    
    async def get_credit_packages(self, credit_type: Optional[CreditType] = None) -> List[CreditPackage]:
        """
        Get available credit packages.
        
        Args:
            credit_type: Filter by credit type
            
        Returns:
            List of available credit packages
        """
        packages = list(self.credit_packages.values())
        
        if credit_type:
            packages = [pkg for pkg in packages if pkg.credit_type == credit_type]
        
        # Sort by price
        packages.sort(key=lambda x: x.price)
        
        return packages
    
    async def create_payment(
        self,
        user_id: str,
        payment_request: PaymentRequest,
        user_email: Optional[str] = None
    ) -> PaymentResponse:
        """
        Create a new payment for credit purchase.
        
        Args:
            user_id: User identifier
            payment_request: Payment request details
            user_email: User email for Stripe customer
            
        Returns:
            Payment response with payment details
        """
        try:
            # Validate package exists
            package = self.credit_packages.get(payment_request.package_id)
            if not package:
                raise ValueError(f"Invalid package ID: {payment_request.package_id}")
            
            # Create payment record
            payment_id = str(uuid4())
            payment_data = {
                "id": payment_id,
                "user_id": user_id,
                "package_id": package.id,
                "amount": float(package.price),
                "currency": "USD",
                "status": PaymentStatus.PENDING.value,
                "payment_method": payment_request.payment_method.value,
                "credits": package.credits,
                "bonus_credits": package.bonus_credits,
                "credit_type": package.credit_type.value,
                "metadata": payment_request.metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc).replace(microsecond=0) + 
                             datetime.timedelta(hours=24)).isoformat()
            }
            
            # Store payment in database
            result = self.supabase_client.table("payments").insert(payment_data).execute()
            if not result.data:
                raise Exception("Failed to create payment record")
            
            # Create Stripe payment intent if using Stripe
            if payment_request.payment_method in [PaymentMethod.STRIPE_CARD, PaymentMethod.STRIPE_BANK]:
                stripe_result = await stripe_service.create_payment_intent(
                    amount=package.price,
                    currency="USD",
                    user_id=user_id,
                    package=package,
                    metadata=payment_request.metadata
                )
                
                # Update payment with Stripe details
                update_data = {
                    "stripe_payment_intent_id": stripe_result["payment_id"],
                    "client_secret": stripe_result["client_secret"]
                }
                
                self.supabase_client.table("payments").update(update_data).eq("id", payment_id).execute()
                
                return PaymentResponse(
                    payment_id=payment_id,
                    status=PaymentStatus.PENDING,
                    package=package,
                    amount=package.price,
                    currency="USD",
                    client_secret=stripe_result["client_secret"],
                    expires_at=stripe_result["expires_at"],
                    created_at=datetime.now(timezone.utc)
                )
            
            # For other payment methods, return basic response
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.PENDING,
                package=package,
                amount=package.price,
                currency="USD",
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error creating payment for user {user_id}: {str(e)}")
            raise
    
    async def process_payment_completion(self, payment_id: str, webhook_data: Dict[str, Any]) -> bool:
        """
        Process payment completion and allocate credits.
        
        Args:
            payment_id: Payment identifier
            webhook_data: Webhook event data
            
        Returns:
            True if processing was successful
        """
        try:
            # Get payment record
            result = self.supabase_client.table("payments").select("*").eq("id", payment_id).execute()
            if not result.data:
                logger.error(f"Payment not found: {payment_id}")
                return False
            
            payment = result.data[0]
            
            # Update payment status
            update_data = {
                "status": webhook_data["status"].value,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "transaction_id": webhook_data.get("transaction_id"),
                "webhook_metadata": webhook_data.get("metadata", {})
            }
            
            self.supabase_client.table("payments").update(update_data).eq("id", payment_id).execute()
            
            # If payment succeeded, allocate credits
            if webhook_data["status"] == PaymentStatus.COMPLETED:
                await self._allocate_credits(payment)
                logger.info(f"Credits allocated for payment {payment_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing payment completion {payment_id}: {str(e)}")
            return False
    
    async def _allocate_credits(self, payment: Dict[str, Any]) -> None:
        """
        Allocate credits to user after successful payment.
        
        Args:
            payment: Payment record
        """
        try:
            user_id = payment["user_id"]
            credits = payment["credits"]
            bonus_credits = payment.get("bonus_credits", 0)
            credit_type = payment["credit_type"]
            total_credits = credits + bonus_credits
            
            # Allocate credits based on type
            if credit_type == CreditType.PROBLEM_GENERATOR.value:
                # Add problem generator credits
                await self.credit_service.add_problem_generator_credits(
                    user_id=user_id,
                    credits=total_credits,
                    reason=f"Credit purchase - Payment {payment['id']}"
                )
            else:
                # Add general credits
                await self.credit_service.add_credits(
                    user_id=user_id,
                    credits=total_credits,
                    reason=f"Credit purchase - Payment {payment['id']}"
                )
            
            # Log credit allocation
            await self.audit_service.log_credit_operation(
                user_id=user_id,
                action="credit_purchase",
                credits_before=0,  # We don't have the before state here
                credits_after=total_credits,
                metadata={
                    "payment_id": payment["id"],
                    "package_id": payment["package_id"],
                    "credits_purchased": credits,
                    "bonus_credits": bonus_credits,
                    "credit_type": credit_type
                }
            )
            
            logger.info(f"Allocated {total_credits} {credit_type} credits to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error allocating credits for payment {payment['id']}: {str(e)}")
            raise
    
    async def get_payment_history(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> PaymentListResponse:
        """
        Get user's payment history.
        
        Args:
            user_id: User identifier
            page: Page number
            per_page: Items per page
            
        Returns:
            Payment history response
        """
        try:
            offset = (page - 1) * per_page
            
            # Get total count
            count_result = self.supabase_client.table("payments").select("id", count="exact").eq("user_id", user_id).execute()
            total_count = count_result.count or 0
            
            # Get payments
            result = self.supabase_client.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
            
            payments = []
            for payment_data in result.data:
                # Get package details
                package = self.credit_packages.get(payment_data["package_id"])
                if not package:
                    continue
                
                payment_history = PaymentHistory(
                    payment_id=payment_data["id"],
                    user_id=payment_data["user_id"],
                    package=package,
                    amount=Decimal(str(payment_data["amount"])),
                    currency=payment_data["currency"],
                    status=PaymentStatus(payment_data["status"]),
                    payment_method=PaymentMethod(payment_data["payment_method"]),
                    credits_granted=payment_data["credits"] + payment_data.get("bonus_credits", 0),
                    transaction_id=payment_data.get("transaction_id"),
                    created_at=datetime.fromisoformat(payment_data["created_at"].replace('Z', '+00:00')),
                    completed_at=datetime.fromisoformat(payment_data["completed_at"].replace('Z', '+00:00')) if payment_data.get("completed_at") else None,
                    metadata=payment_data.get("metadata", {})
                )
                payments.append(payment_history)
            
            return PaymentListResponse(
                payments=payments,
                total_count=total_count,
                page=page,
                per_page=per_page
            )
            
        except Exception as e:
            logger.error(f"Error getting payment history for user {user_id}: {str(e)}")
            raise
    
    async def get_payment_status(self, payment_id: str, user_id: str) -> Optional[PaymentResponse]:
        """
        Get payment status.
        
        Args:
            payment_id: Payment identifier
            user_id: User identifier
            
        Returns:
            Payment response or None if not found
        """
        try:
            result = self.supabase_client.table("payments").select("*").eq("id", payment_id).eq("user_id", user_id).execute()
            
            if not result.data:
                return None
            
            payment_data = result.data[0]
            package = self.credit_packages.get(payment_data["package_id"])
            
            if not package:
                return None
            
            return PaymentResponse(
                payment_id=payment_data["id"],
                status=PaymentStatus(payment_data["status"]),
                package=package,
                amount=Decimal(str(payment_data["amount"])),
                currency=payment_data["currency"],
                client_secret=payment_data.get("client_secret"),
                created_at=datetime.fromisoformat(payment_data["created_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"Error getting payment status {payment_id}: {str(e)}")
            raise


# Global service instance
payment_service = PaymentService()
