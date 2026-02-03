"""
Stripe Payment Service

This service handles Stripe integration for payment processing including:
1. Payment intent creation
2. Payment confirmation
3. Webhook handling
4. Customer management
"""

import os
import logging
import stripe
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

from ..system.core.supabase_client import get_service_role_client
from .models import PaymentStatus, PaymentMethod, CreditPackage

# Configure logging
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")


class StripeService:
    """Service for handling Stripe payment operations."""
    
    def __init__(self):
        """Initialize Stripe service."""
        self.supabase_client = get_service_role_client()
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not stripe.api_key:
            logger.warning("Stripe API key not configured - payment processing will be disabled")
        
        logger.info("StripeService initialized")
    
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        package: CreditPackage,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe payment intent.
        
        Args:
            amount: Payment amount in cents
            currency: Payment currency (e.g., 'usd')
            user_id: User identifier
            package: Credit package being purchased
            metadata: Additional metadata
            
        Returns:
            Dict containing payment intent details
        """
        try:
            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)
            
            # Prepare metadata
            intent_metadata = {
                "user_id": user_id,
                "package_id": package.id,
                "credits": str(package.credits),
                "credit_type": package.credit_type.value,
                "bonus_credits": str(package.bonus_credits)
            }
            
            if metadata:
                intent_metadata.update(metadata)
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=intent_metadata,
                automatic_payment_methods={
                    'enabled': True,
                },
                description=f"Credit Purchase: {package.name}"
            )
            
            logger.info(f"Created Stripe payment intent {intent.id} for user {user_id}")
            
            return {
                "payment_id": intent.id,
                "client_secret": intent.client_secret,
                "amount": amount,
                "currency": currency,
                "status": self._map_stripe_status(intent.status),
                "expires_at": datetime.utcnow() + timedelta(hours=24)  # Stripe default
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise Exception(f"Payment processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    async def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Confirm a payment intent status.
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Dict containing payment status
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "payment_id": intent.id,
                "status": self._map_stripe_status(intent.status),
                "amount": Decimal(intent.amount) / 100,
                "currency": intent.currency.upper(),
                "metadata": intent.metadata
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {str(e)}")
            raise Exception(f"Payment confirmation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error confirming payment: {str(e)}")
            raise
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """
        Handle Stripe webhook events.
        
        Args:
            payload: Webhook payload
            signature: Stripe signature header
            
        Returns:
            Dict containing event data or None if not handled
        """
        try:
            if not self.webhook_secret:
                logger.warning("Stripe webhook secret not configured")
                return None
            
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                return await self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return await self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'payment_intent.canceled':
                return await self._handle_payment_canceled(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
                return None
                
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {str(e)}")
            raise Exception("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Error handling Stripe webhook: {str(e)}")
            raise
    
    async def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment."""
        logger.info(f"Payment succeeded: {payment_intent['id']}")
        
        return {
            "event_type": "payment_succeeded",
            "payment_id": payment_intent['id'],
            "status": PaymentStatus.COMPLETED,
            "metadata": payment_intent.get('metadata', {}),
            "amount": Decimal(payment_intent['amount']) / 100,
            "currency": payment_intent['currency'].upper()
        }
    
    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment."""
        logger.info(f"Payment failed: {payment_intent['id']}")
        
        return {
            "event_type": "payment_failed",
            "payment_id": payment_intent['id'],
            "status": PaymentStatus.FAILED,
            "metadata": payment_intent.get('metadata', {}),
            "error": payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
        }
    
    async def _handle_payment_canceled(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle canceled payment."""
        logger.info(f"Payment canceled: {payment_intent['id']}")
        
        return {
            "event_type": "payment_canceled",
            "payment_id": payment_intent['id'],
            "status": PaymentStatus.CANCELLED,
            "metadata": payment_intent.get('metadata', {})
        }
    
    def _map_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe status to internal PaymentStatus."""
        status_map = {
            'requires_payment_method': PaymentStatus.PENDING,
            'requires_confirmation': PaymentStatus.PENDING,
            'requires_action': PaymentStatus.PENDING,
            'processing': PaymentStatus.PROCESSING,
            'succeeded': PaymentStatus.COMPLETED,
            'canceled': PaymentStatus.CANCELLED,
            'requires_capture': PaymentStatus.PROCESSING
        }
        
        return status_map.get(stripe_status, PaymentStatus.FAILED)
    
    async def create_customer(self, user_id: str, email: str, name: Optional[str] = None) -> str:
        """
        Create a Stripe customer.
        
        Args:
            user_id: Internal user ID
            email: Customer email
            name: Customer name
            
        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            raise Exception(f"Customer creation error: {str(e)}")
    
    async def get_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """
        Get customer's payment methods.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            List of payment methods
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year
                    } if pm.type == "card" else None
                }
                for pm in payment_methods.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting payment methods: {str(e)}")
            raise Exception(f"Payment methods retrieval error: {str(e)}")


# Global service instance
stripe_service = StripeService()
