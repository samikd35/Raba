"""
Subscription management module for the MINT API.

This module handles subscription plans, quotas, and rate limiting.
It includes models for subscription plans and middleware for enforcing quotas.
"""

import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import logging
from enum import Enum

from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from src.mint.api.supabase_client import SupabaseClient
from src.mint.api.auth import get_current_user_id

# Configure logging
logger = logging.getLogger(__name__)


# Define subscription plan tiers
class PlanTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


# Model for subscription plans
class SubscriptionPlan(BaseModel):
    id: str
    name: str
    monthly_quota: int
    price_usd: float
    features: Optional[Dict[str, Any]] = None


# Model for user subscriptions
class UserSubscription(BaseModel):
    user_id: str
    plan_id: str
    renewal_date: datetime
    subscription_id: Optional[str] = None  # Stripe subscription ID if applicable
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None


class QuotaManager:
    """Manager for handling subscription quotas and rate limits."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize the quota manager.
        
        Args:
            supabase_client: The Supabase client to use for database access
        """
        self.supabase_client = supabase_client
        self.plans_table = "plans"
        self.user_subscriptions_table = "user_subscriptions"
        self.jobs_table = "mint_jobs"
        
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a subscription plan by ID.
        
        Args:
            plan_id: The ID of the plan to retrieve
            
        Returns:
            Optional[Dict]: The plan data if found, None otherwise
        """
        try:
            response = self.supabase_client.client.table(self.plans_table) \
                .select("*") \
                .eq("id", plan_id) \
                .execute()
                
            plans = response.data
            return plans[0] if plans else None
            
        except Exception as e:
            logger.error(f"Error getting plan {plan_id}: {e}")
            return None
            
    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's active subscription.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Optional[Dict]: The subscription data if found, None otherwise
        """
        try:
            response = self.supabase_client.client.table(self.user_subscriptions_table) \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("is_active", True) \
                .execute()
                
            subscriptions = response.data
            return subscriptions[0] if subscriptions else None
            
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            return None
    
    def get_user_job_count_this_cycle(self, user_id: str) -> int:
        """
        Get the count of jobs created by a user in the current billing cycle.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            int: The number of jobs created in the current cycle
        """
        try:
            # Get the user's subscription to determine the renewal date
            subscription = self.get_user_subscription(user_id)
            
            if not subscription:
                # If no subscription found, return 0 (will be handled by assigning free plan)
                return 0
                
            # Calculate the start of the current billing cycle
            renewal_date = subscription.get("renewal_date")
            if not renewal_date:
                return 0
                
            # Parse the renewal date
            if isinstance(renewal_date, str):
                renewal_date = datetime.fromisoformat(renewal_date.replace('Z', '+00:00'))
                
            # Find the start of the current billing cycle
            today = datetime.utcnow()
            months_diff = (today.year - renewal_date.year) * 12 + today.month - renewal_date.month
            
            # Calculate the start date of the current cycle
            if months_diff >= 0:
                cycle_start = datetime(
                    year=renewal_date.year,
                    month=renewal_date.month,
                    day=renewal_date.day
                ) + timedelta(days=30 * months_diff)
            else:
                # If somehow the renewal date is in the future, use it as the cycle start
                cycle_start = renewal_date
                
            # Count jobs created since the cycle start
            response = self.supabase_client.client.table(self.jobs_table) \
                .select("count", count="exact") \
                .eq("user_id", user_id) \
                .gte("created_at", cycle_start.isoformat()) \
                .execute()
                
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error getting job count for user {user_id}: {e}")
            return 0
            
    def user_has_quota_available(self, user_id: str) -> bool:
        """
        Check if a user has quota available for a new job.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            bool: True if quota available, False otherwise
        """
        try:
            # Get the user's subscription
            subscription = self.get_user_subscription(user_id)
            
            # If no subscription found, assign free tier
            if not subscription:
                # Get the free plan ID from environment variable or use default
                free_plan_id = os.getenv("FREE_PLAN_ID", "free")
                
                # Look up the free plan
                free_plan = self.get_plan(free_plan_id)
                
                if not free_plan:
                    logger.error(f"Free plan {free_plan_id} not found")
                    return False
                    
                # The user has the free plan's quota
                monthly_quota = free_plan.get("monthly_quota", 3)  # Default: 3 jobs/month
            else:
                # Get the plan for this subscription
                plan = self.get_plan(subscription.get("plan_id"))
                
                if not plan:
                    logger.error(f"Plan {subscription.get('plan_id')} not found")
                    return False
                    
                monthly_quota = plan.get("monthly_quota", 0)
                
            # Get the user's job count this cycle
            job_count = self.get_user_job_count_this_cycle(user_id)
            
            # Check if the user has quota available
            return job_count < monthly_quota
            
        except Exception as e:
            logger.error(f"Error checking quota for user {user_id}: {e}")
            return False
            
    async def enforce_quota(self, user_id: str):
        """
        Enforce quota limits for a user. Raises an HTTPException if quota exceeded.
        
        Args:
            user_id: The ID of the user
            
        Raises:
            HTTPException: If the user has exceeded their quota
        """
        if not self.user_has_quota_available(user_id):
            # Get subscription info for better error messaging
            subscription = self.get_user_subscription(user_id)
            
            if subscription:
                plan = self.get_plan(subscription.get("plan_id"))
                plan_name = plan.get("name", "current") if plan else "current"
            else:
                plan_name = "free"
                
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Quota exceeded for your {plan_name} plan. "
                    "Please upgrade your subscription to continue."
                )
            )


class QuotaMiddleware(BaseHTTPMiddleware):
    """
    Middleware for enforcing quota limits on job creation endpoints.
    """
    
    def __init__(
        self,
        app,
        supabase_client: SupabaseClient,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the quota middleware.
        
        Args:
            app: The FastAPI application
            supabase_client: The Supabase client to use for database access
            exclude_paths: List of paths to exclude from quota enforcement
        """
        super().__init__(app)
        self.quota_manager = QuotaManager(supabase_client)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/openapi.json",
            "/health",
            "/webhooks/stripe",
            "/jobs"
        ]
        
    async def dispatch(self, request: Request, call_next):
        """
        Process the request, checking quota if needed.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response from the next handler
        """
        # Skip quota enforcement for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
            
        # Skip quota enforcement for non-POST requests
        if request.method != "POST" or not path.startswith("/jobs"):
            return await call_next(request)
            
        # For job creation endpoint, enforce quota
        if path == "/jobs" and hasattr(request.state, "user_id"):
            user_id = request.state.user_id
            
            # Check quota before proceeding
            await self.quota_manager.enforce_quota(user_id)
            
        # Continue processing the request
        response = await call_next(request)
        return response


# SQL to create the subscription-related tables
"""
-- Create plans table
CREATE TABLE public.plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    monthly_quota INTEGER NOT NULL,
    price_usd NUMERIC(10, 2) NOT NULL,
    features JSONB
);

-- Create user_subscriptions table
CREATE TABLE public.user_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL REFERENCES public.plans(id),
    renewal_date TIMESTAMP WITH TIME ZONE NOT NULL,
    subscription_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index on user_id for faster lookups
CREATE INDEX user_subscriptions_user_id_idx ON public.user_subscriptions (user_id);

-- Insert some default plans
INSERT INTO public.plans (id, name, monthly_quota, price_usd, features)
VALUES
    ('free', 'Free Tier', 3, 0.00, '{"max_clarifications": 1, "support": "community"}'),
    ('basic', 'Basic', 10, 19.99, '{"max_clarifications": 3, "support": "email"}'),
    ('standard', 'Standard', 50, 49.99, '{"max_clarifications": 5, "support": "priority"}'),
    ('premium', 'Premium', 500, 199.99, '{"max_clarifications": 10, "support": "dedicated"}');

-- Grant access to authenticated users for select
GRANT SELECT ON public.plans TO authenticated;

-- Grant access to authenticated users for their own subscriptions
GRANT SELECT ON public.user_subscriptions TO authenticated;

-- Create RLS policy for user_subscriptions
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own subscriptions" ON public.user_subscriptions
    FOR SELECT
    USING (auth.uid() = user_id);
"""
