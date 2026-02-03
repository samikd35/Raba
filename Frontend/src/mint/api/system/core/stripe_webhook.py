"""
Stripe webhook handler for the MINT API.

This module handles incoming Stripe webhook events for subscription management.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from dotenv import load_dotenv

from src.mint.api.supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_client = get_service_role_client()

# Define table names
USER_SUBSCRIPTIONS_TABLE = "user_subscriptions"

# Create router
router = APIRouter()


async def _get_user_id_from_stripe_customer(customer_id: str) -> Optional[str]:
    """
    Get the user ID associated with a Stripe customer ID.
    
    Args:
        customer_id: The Stripe customer ID
        
    Returns:
        Optional[str]: The associated user ID if found
    """
    try:
        # Query Supabase auth.users table to find the user with this customer ID
        # Note: This assumes you have a stripe_customer_id column in your users table
        response = supabase_client.client.table("users") \
            .select("id") \
            .eq("stripe_customer_id", customer_id) \
            .single() \
            .execute()
        
        user_data = response.data
        return user_data.get("id") if user_data else None
    
    except Exception as e:
        logger.error(f"Error finding user for Stripe customer {customer_id}: {e}")
        return None


async def _update_user_subscription(
    user_id: str,
    plan_id: str,
    subscription_id: str,
    renewal_date: datetime
) -> bool:
    """
    Update a user's subscription in the database.
    
    Args:
        user_id: The user's ID
        plan_id: The subscription plan ID
        subscription_id: The Stripe subscription ID
        renewal_date: The next renewal date
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First check if the user already has an active subscription
        response = supabase_client.client.table(USER_SUBSCRIPTIONS_TABLE) \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("is_active", True) \
            .execute()
        
        existing_subscriptions = response.data
        
        if existing_subscriptions:
            # Update the existing subscription
            existing_id = existing_subscriptions[0].get("id")
            
            response = supabase_client.client.table(USER_SUBSCRIPTIONS_TABLE) \
                .update({
                    "plan_id": plan_id,
                    "subscription_id": subscription_id,
                    "renewal_date": renewal_date.isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }) \
                .eq("id", existing_id) \
                .execute()
            
            return bool(response.data)
        else:
            # Create a new subscription
            response = supabase_client.client.table(USER_SUBSCRIPTIONS_TABLE) \
                .insert({
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "subscription_id": subscription_id,
                    "renewal_date": renewal_date.isoformat(),
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }) \
                .execute()
            
            return bool(response.data)
    
    except Exception as e:
        logger.error(f"Error updating subscription for user {user_id}: {e}")
        return False


async def _cancel_user_subscription(subscription_id: str) -> bool:
    """
    Cancel a user's subscription in the database.
    
    Args:
        subscription_id: The Stripe subscription ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Find the subscription by Stripe subscription ID
        response = supabase_client.client.table(USER_SUBSCRIPTIONS_TABLE) \
            .select("*") \
            .eq("subscription_id", subscription_id) \
            .execute()
        
        subscriptions = response.data
        
        if not subscriptions:
            logger.warning(f"Subscription {subscription_id} not found in database")
            return False
        
        # Update the subscription to inactive
        subscription_id = subscriptions[0].get("id")
        
        response = supabase_client.client.table(USER_SUBSCRIPTIONS_TABLE) \
            .update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            }) \
            .eq("id", subscription_id) \
            .execute()
        
        return bool(response.data)
    
    except Exception as e:
        logger.error(f"Error canceling subscription {subscription_id}: {e}")
        return False


def _get_plan_id_from_stripe_price(price_id: str) -> Optional[str]:
    """
    Map Stripe price ID to our internal plan ID.
    
    Args:
        price_id: The Stripe price ID
        
    Returns:
        Optional[str]: The internal plan ID
    """
    # This mapping should be stored in the database for production
    # For now, we use a simple dictionary
    price_to_plan_map = {
        os.getenv("STRIPE_PRICE_BASIC", "price_basic"): "basic",
        os.getenv("STRIPE_PRICE_STANDARD", "price_standard"): "standard",
        os.getenv("STRIPE_PRICE_PREMIUM", "price_premium"): "premium",
    }
    
    return price_to_plan_map.get(price_id, "free")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Handle incoming Stripe webhook events.
    
    This endpoint processes subscription-related events from Stripe
    and updates the user_subscriptions table accordingly.
    """
    # Get the raw request body
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")
    
    try:
        # Verify the event with Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle subscription events
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info(f"Processing Stripe event: {event_type}")
    
    try:
        if event_type == "customer.subscription.created" or event_type == "customer.subscription.updated":
            # Get the customer ID and subscription details
            customer_id = data.get("customer")
            subscription_id = data.get("id")
            current_period_end = data.get("current_period_end")
            
            # Get the price ID from the first item (assumes one plan per subscription)
            items = data.get("items", {}).get("data", [])
            if not items:
                logger.error(f"No items found in subscription {subscription_id}")
                return {"status": "error", "message": "No subscription items found"}
                
            price_id = items[0].get("price", {}).get("id")
            if not price_id:
                logger.error(f"No price ID found for subscription {subscription_id}")
                return {"status": "error", "message": "No price ID found"}
            
            # Map price ID to plan ID
            plan_id = _get_plan_id_from_stripe_price(price_id)
            
            # Get the user ID from the customer ID
            user_id = await _get_user_id_from_stripe_customer(customer_id)
            if not user_id:
                logger.error(f"No user found for Stripe customer {customer_id}")
                return {"status": "error", "message": "User not found"}
            
            # Calculate renewal date
            renewal_date = datetime.fromtimestamp(current_period_end)
            
            # Update the user's subscription
            success = await _update_user_subscription(
                user_id=user_id,
                plan_id=plan_id,
                subscription_id=subscription_id,
                renewal_date=renewal_date
            )
            
            if not success:
                logger.error(f"Failed to update subscription for user {user_id}")
                return {"status": "error", "message": "Failed to update subscription"}
            
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription_id = data.get("id")
            
            # Cancel the subscription in our database
            success = await _cancel_user_subscription(subscription_id)
            
            if not success:
                logger.error(f"Failed to cancel subscription {subscription_id}")
                return {"status": "error", "message": "Failed to cancel subscription"}
        
        return {"status": "ok", "data": {"processed": True}}
        
    except Exception as e:
        logger.error(f"Error processing Stripe event {event_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )
