"""
Async Stripe operations for high-performance payment processing.

Uses the official Stripe async support with httpx for non-blocking API calls.
All payment methods are enabled automatically by Stripe.
"""

import os
import logging
from typing import Optional, Dict, Any

import stripe
from stripe import StripeClient
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Global async-capable Stripe client
_stripe_client: Optional[StripeClient] = None


def get_stripe_client() -> StripeClient:
    """
    Get singleton Stripe client with async support via httpx.
    """
    global _stripe_client
    if _stripe_client is None:
        api_key = os.getenv("STRIPE_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Payment service configuration error. Please contact support."
            )
        _stripe_client = StripeClient(
            api_key=api_key,
            http_client=stripe.HTTPXClient()  # Enables async operations
        )
        logger.info("Async Stripe client initialized with httpx")
    return _stripe_client


def get_webhook_secret() -> str:
    """Get Stripe webhook secret."""
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Webhook configuration error. Please contact support."
        )
    return secret


async def create_checkout_session_async(
    *,
    currency: str,
    amount_cents: int,
    product_name: str,
    product_description: str,
    success_url: str,
    cancel_url: str,
    client_reference_id: str,
    customer_email: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a Stripe checkout session asynchronously.

    All payment methods are enabled automatically by Stripe based on currency
    and customer location. This includes cards, bank transfers, wallets, etc.

    Args:
        currency: 3-letter currency code (e.g., 'usd', 'ngn')
        amount_cents: Amount in smallest currency unit (cents)
        product_name: Name shown on checkout page
        product_description: Description shown on checkout page
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if customer cancels
        client_reference_id: Your reference ID (tx_ref)
        customer_email: Pre-fill customer email on checkout
        metadata: Additional metadata to store with the session

    Returns:
        Dict with session details including 'url' and 'id'
    """
    client = get_stripe_client()

    try:
        params = {
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": product_name,
                            "description": product_description,
                        },
                    },
                    "quantity": 1,
                }
            ],
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": client_reference_id,
            "customer_email": customer_email,
            "metadata": metadata or {},
        }
        session = await client.checkout.sessions.create_async(params)

        return {
            "id": session.id,
            "url": session.url,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "client_reference_id": session.client_reference_id,
        }

    except stripe.error.CardError as e:
        logger.error(f"Card error creating checkout session: {e}")
        raise HTTPException(
            status_code=400,
            detail="Your card was declined. Please try a different payment method."
        )
    except stripe.error.RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Payment service is temporarily busy. Please try again in a few seconds."
        )
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Invalid request to Stripe: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid payment request. Please check your details and try again."
        )
    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe authentication error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Payment service configuration error. Please contact support."
        )
    except stripe.error.APIConnectionError as e:
        logger.error(f"Stripe connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to payment service. Please try again."
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Payment processing error. Please try again or contact support."
        )
    except Exception as e:
        logger.exception(f"Unexpected error creating checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again or contact support."
        )


async def retrieve_checkout_session_async(session_id: str) -> Dict[str, Any]:
    """
    Retrieve a Stripe checkout session asynchronously.

    Args:
        session_id: The Stripe session ID to retrieve

    Returns:
        Dict with session details
    """
    client = get_stripe_client()

    try:
        session = await client.checkout.sessions.retrieve_async(session_id)

        return {
            "id": session.id,
            "url": session.url,
            "payment_status": session.payment_status,
            "payment_intent": session.payment_intent,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "client_reference_id": session.client_reference_id,
            "customer_email": session.customer_email,
            "metadata": dict(session.metadata) if session.metadata else {},
        }

    except stripe.error.InvalidRequestError as e:
        logger.error(f"Invalid session ID: {e}")
        raise HTTPException(
            status_code=404,
            detail="Payment session not found. It may have expired or been cancelled."
        )
    except stripe.error.APIConnectionError as e:
        logger.error(f"Stripe connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to payment service. Please try again."
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to verify payment. Please try again or contact support."
        )
    except Exception as e:
        logger.exception(f"Unexpected error retrieving session: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again or contact support."
        )


def verify_webhook_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """
    Verify Stripe webhook signature and construct event.

    This is synchronous as it's CPU-bound cryptographic verification.

    Args:
        payload: Raw request body bytes
        sig_header: Stripe-Signature header value

    Returns:
        Verified Stripe event dict
    """
    webhook_secret = get_webhook_secret()

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        return event
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
