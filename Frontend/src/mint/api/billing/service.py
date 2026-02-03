"""
Billing service for managing organization billing, invoices, and pricing.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg2
import psycopg2.extras
import stripe
from psycopg2 import pool
from psycopg2.extensions import connection as PgConnection

from ..system.core.supabase_client import get_supabase_client
from ..services.communication.email_service import email_service
from .service_transactions import (
    create_invoice_with_stripe_atomic,
    consume_credits_fifo_atomic
)

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_API_KEY')


class BillingError(Exception):
    """Base exception for billing errors"""
    pass


class InsufficientCreditsError(BillingError):
    """Raised when organization has insufficient credits for admin seat billing"""
    pass


class InvoiceNotFoundError(BillingError):
    """Raised when invoice is not found"""
    pass


class InvalidPricingConfigError(BillingError):
    """Raised when pricing configuration is invalid"""
    pass


class BillingService:
    """Service for billing and invoice management operations"""

    def __init__(self, use_service_role: bool = True):
        """Initialize billing service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role

    @staticmethod
    def _now() -> datetime:
        """Get current UTC datetime"""
        return datetime.now(timezone.utc)

    def _get_pg_connection(self) -> PgConnection:
        """
        Get fresh PostgreSQL connection for transactions with retry logic.
        Always creates a new connection instead of reusing to avoid pooler timeouts.
        """
        import psycopg2
        import time

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise BillingError("DATABASE_URL environment variable not set")

        # Retry logic for connection with exponential backoff
        max_retries = 3
        retry_delay = 0.5
        last_error = None

        for attempt in range(max_retries):
            try:
                # Always create a fresh connection for serverless functions
                # Add connection parameters optimized for Supabase pooler
                conn = psycopg2.connect(
                    database_url,
                    connect_timeout=10,
                    options='-c statement_timeout=30000'  # 30 second statement timeout
                )
                if attempt > 0:
                    logger.info(f"Successfully connected to database on attempt {attempt + 1}")
                return conn
            except psycopg2.OperationalError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)[:100]}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts")
                    raise BillingError(f"Failed to connect to database: {str(last_error)}")

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions using raw SQL.
        Creates a fresh connection and closes it after use.
        Usage:
            with billing_service.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO ...")
                # automatically commits on success, rolls back on exception
        """
        conn = self._get_pg_connection()
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            # Always close the connection after transaction
            if conn and not conn.closed:
                conn.close()
                logger.debug("Database connection closed")

    def _execute_sql(self, conn, query: str, params: tuple = None) -> Any:
        """Execute SQL query and return results"""
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            return cursor
        finally:
            cursor.close()

    def _execute_sql_one(self, conn, query: str, params: tuple = None) -> Any:
        """Execute SQL query and return first result"""
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()

    def _get_or_create_stripe_customer(
        self,
        tenant_id: str,
        customer_email: str,
        customer_name: str
    ) -> str:
        """
        Get or create Stripe customer for organization.
        Returns customer_id.
        """
        try:
            # Try to find existing customer by metadata
            customers = stripe.Customer.list(
                email=customer_email,
                limit=1
            )

            if customers.data:
                customer = customers.data[0]
                logger.info(f"Found existing Stripe customer {customer.id}")
            else:
                # Create new customer
                customer = stripe.Customer.create(
                    email=customer_email,
                    name=customer_name,
                    metadata={'tenant_id': tenant_id}
                )
                logger.info(f"Created new Stripe customer {customer.id}")

            return customer.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error managing customer: {e}")
            raise BillingError(f"Failed to manage Stripe customer: {str(e)}")

    def _create_stripe_invoice(
        self,
        tenant_id: str,
        amount_credits: int,
        description: str,
        customer_email: str,
        customer_name: str,
        line_items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        due_days: int = 7,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Create a Stripe Invoice for B2B billing.

        Args:
            tenant_id: Organization tenant ID
            amount_credits: Total amount in credits
            description: Invoice description
            customer_email: Customer email
            customer_name: Customer/organization name
            line_items: List of dicts with 'description', 'amount_cents', and optional 'metadata'
            metadata: Additional metadata for the invoice
            due_days: Days until invoice is due (default 7)
            currency: Currency code (default: USD)

        Returns:
            Dict with Stripe invoice details
        """
        try:
            # Get or create Stripe customer
            customer_id = self._get_or_create_stripe_customer(
                tenant_id=tenant_id,
                customer_email=customer_email,
                customer_name=customer_name
            )

            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer_id,
                collection_method='send_invoice',  # Send invoice for payment
                days_until_due=due_days,
                description=description,
                currency=currency.lower(),
                metadata={
                    'tenant_id': tenant_id,
                    'amount_credits': amount_credits,
                    **(metadata or {})
                }
            )

            # Add line items to invoice
            for item in line_items:
                stripe.InvoiceItem.create(
                    customer=customer_id,
                    invoice=invoice.id,
                    description=item['description'],
                    amount=item['amount_cents'],
                    currency=currency.lower(),
                    metadata=item.get('metadata', {})
                )

            # Finalize the invoice (makes it ready for payment)
            finalized_invoice = stripe.Invoice.finalize_invoice(invoice.id)

            logger.info(f"Created Stripe invoice {finalized_invoice.id} ({finalized_invoice.number}) for {amount_credits} credits")

            return {
                'stripe_invoice_id': finalized_invoice.id,
                'stripe_invoice_number': finalized_invoice.number,
                'hosted_invoice_url': finalized_invoice.hosted_invoice_url,  # Payment page URL
                'invoice_pdf': finalized_invoice.invoice_pdf,
                'amount_credits': amount_credits,
                'status': finalized_invoice.status
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating invoice: {e}")
            raise BillingError(f"Failed to create Stripe invoice: {str(e)}")

    def get_pricing_config(self) -> Dict[str, Any]:
        """
        Get the active pricing configuration.

        Returns:
            Dict containing pricing configuration

        Raises:
            InvalidPricingConfigError: If no active pricing config found
        """
        logger.info("Fetching active pricing configuration")

        response = self.supabase.table('pricing_configuration') \
            .select('*') \
            .eq('is_active', True) \
            .order('effective_from', desc=True) \
            .limit(1) \
            .execute()

        if not response.data:
            raise InvalidPricingConfigError("No active pricing configuration found")

        config = response.data[0]
        logger.info(f"Retrieved pricing config: admin_seat_price={config['admin_seat_price_credits']}, "
                   f"estimated_credits_per_user={config['estimated_credits_per_user']}")

        return config

    def update_pricing_config(
        self,
        admin_seat_price_credits: int,
        estimated_credits_per_user: int,
        created_by: str
    ) -> Dict[str, Any]:
        """
        Update pricing configuration (super admin only).
        Deactivates current config and creates new one.

        Args:
            admin_seat_price_credits: New price for admin seats in credits
            estimated_credits_per_user: New estimated credits per user
            created_by: User ID of the admin making the change

        Returns:
            Dict containing new pricing configuration

        Raises:
            InvalidPricingConfigError: If invalid pricing values provided
        """
        if admin_seat_price_credits < 0 or estimated_credits_per_user < 0:
            raise InvalidPricingConfigError("Pricing values must be non-negative")

        logger.info(f"Updating pricing config: admin_seat={admin_seat_price_credits}, "
                   f"est_credits={estimated_credits_per_user}, created_by={created_by}")

        # Deactivate current config
        now = self._now()

        current_response = self.supabase.table('pricing_configuration') \
            .select('id') \
            .eq('is_active', True) \
            .execute()

        if current_response.data:
            for config in current_response.data:
                self.supabase.table('pricing_configuration') \
                    .update({
                        'is_active': False,
                        'effective_until': now.isoformat(),
                        'updated_at': now.isoformat()
                    }) \
                    .eq('id', config['id']) \
                    .execute()

        # Create new config
        new_config_data = {
            'admin_seat_price_credits': admin_seat_price_credits,
            'estimated_credits_per_user': estimated_credits_per_user,
            'is_active': True,
            'effective_from': now.isoformat(),
            'created_by': created_by
        }

        new_config_response = self.supabase.table('pricing_configuration') \
            .insert(new_config_data) \
            .execute()

        if not new_config_response.data:
            raise BillingError("Failed to create new pricing configuration")

        logger.info(f"Created new pricing config: {new_config_response.data[0]['id']}")

        return new_config_response.data[0]

    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an invoice for a postpay_org organization with Stripe integration.
        Uses database transactions for atomicity.

        Args:
            tenant_id: Organization tenant ID
            period_start: Start of billing period
            period_end: End of billing period

        Returns:
            Dict containing invoice data with Stripe payment URL, or None if no activity

        Raises:
            BillingError: If invoice generation fails
        """
        logger.info(f"Generating invoice for tenant {tenant_id}, period {period_start} to {period_end}")

        # Verify organization is postpay_org (READ using Supabase - outside transaction)
        org_config_response = self.supabase.table('organization_billing_config') \
            .select('organization_type, billing_settings, tenants!inner(name)') \
            .eq('tenant_id', tenant_id) \
            .single() \
            .execute()

        if not org_config_response.data:
            raise BillingError(f"No billing config found for tenant {tenant_id}")

        if org_config_response.data['organization_type'] != 'postpay_org':
            raise BillingError(f"Tenant {tenant_id} is not a postpay organization")

        tenant_name = org_config_response.data['tenants']['name']
        billing_settings = org_config_response.data.get('billing_settings') or {}
        currency = billing_settings.get('currency', 'USD')

        # Skip if an invoice already exists for this tenant and period
        existing_invoice_response = self.supabase.table('invoices') \
            .select('id, invoice_number, total_amount_credits, issued_at, due_date, status, stripe_invoice_id, metadata') \
            .eq('tenant_id', tenant_id) \
            .eq('period_start', period_start.isoformat()) \
            .eq('period_end', period_end.isoformat()) \
            .limit(1) \
            .execute()

        if existing_invoice_response.data:
            existing_invoice = existing_invoice_response.data[0]
            metadata = existing_invoice.get('metadata') or {}
            logger.info(
                f"Invoice already exists for tenant {tenant_id}, period {period_start} to {period_end}: "
                f"{existing_invoice['invoice_number']}"
            )
            return {
                'already_invoiced': True,
                'id': existing_invoice['id'],
                'invoice_number': existing_invoice['invoice_number'],
                'tenant_id': tenant_id,
                'stripe_invoice_id': existing_invoice.get('stripe_invoice_id'),
                'stripe_invoice_number': metadata.get('stripe_invoice_number'),
                'stripe_hosted_url': metadata.get('stripe_hosted_url'),
                'stripe_pdf_url': metadata.get('stripe_pdf_url'),
                'total_amount_credits': existing_invoice.get('total_amount_credits'),
                'issued_at': existing_invoice.get('issued_at'),
                'due_date': existing_invoice.get('due_date'),
                'status': existing_invoice.get('status')
            }

        # Get pricing configuration
        pricing = self.get_pricing_config()
        admin_seat_price = pricing['admin_seat_price_credits']

        # Calculate credits allocated during period
        # For postpay_org, use organization_credit_allocations table
        # This tracks all credit allocations (purchases, grants, member assignments)
        # independent of consumption
        # IMPORTANT: Also select 'id' to mark allocations as invoiced later
        allocations_response = self.supabase.table('organization_credit_allocations') \
            .select('id, credit_amount') \
            .eq('tenant_id', tenant_id) \
            .gte('allocated_at', period_start.isoformat()) \
            .lt('allocated_at', period_end.isoformat()) \
            .is_('invoice_id', 'null') \
            .execute()

        allocation_ids = [alloc['id'] for alloc in allocations_response.data] if allocations_response.data else []
        total_credits_allocated = sum(
            alloc['credit_amount'] for alloc in allocations_response.data
        ) if allocations_response.data else 0

        # Store allocation IDs for marking as invoiced later
        allocation_ids = [alloc['id'] for alloc in allocations_response.data] if allocations_response.data else []

        # Count current admin seats
        admin_seats_response = self.supabase.table('tenant_memberships') \
            .select('id', count='exact') \
            .eq('tenant_id', tenant_id) \
            .eq('role', 'admin') \
            .eq('is_active', True) \
            .execute()

        admin_seats_count = admin_seats_response.count or 0
        admin_seat_charges = admin_seats_count * admin_seat_price

        # Count total members
        members_response = self.supabase.table('tenant_memberships') \
            .select('id', count='exact') \
            .eq('tenant_id', tenant_id) \
            .eq('is_active', True) \
            .execute()

        members_count = members_response.count or 0

        # Calculate total
        total_amount_credits = total_credits_allocated + admin_seat_charges

        # Skip if no activity
        if total_amount_credits == 0:
            logger.info(f"No activity to bill for tenant {tenant_id}")
            return None

        # Get org owner email for Stripe
        owner_response = self.supabase.table('tenant_memberships') \
            .select('user_profiles!inner(email)') \
            .eq('tenant_id', tenant_id) \
            .eq('role', 'owner') \
            .eq('is_active', True) \
            .limit(1) \
            .execute()

        customer_email = owner_response.data[0]['user_profiles']['email'] if owner_response.data else None

        # Get exchange rate to convert credits to fiat amount
        from ..payment_v2_stripe.service import PaymentService
        payment_service = PaymentService()
        rate = payment_service.get_credits_per_unit(currency)

        # Build Stripe line items
        stripe_line_items = []

        if total_credits_allocated > 0:
            # Calculate fiat amount from credits
            allocation_amount = float(Decimal(str(total_credits_allocated)) / Decimal(str(rate)))
            stripe_line_items.append({
                'description': f'Credits allocated during {period_start.strftime("%B %Y")}',
                'amount_cents': int(allocation_amount * 100),
                'metadata': {
                    'item_type': 'credit_allocation',
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat()
                }
            })

        if admin_seat_charges > 0:
            # Calculate fiat amount from credits
            seat_amount = float(Decimal(str(admin_seat_charges)) / Decimal(str(rate)))
            stripe_line_items.append({
                'description': f'Admin seat charges ({admin_seats_count} seats × {admin_seat_price} credits)',
                'amount_cents': int(seat_amount * 100),
                'metadata': {
                    'item_type': 'admin_seat',
                    'admin_seats_count': admin_seats_count,
                    'seat_price': admin_seat_price
                }
            })

        # Create Stripe invoice FIRST (outside transaction)
        stripe_invoice = self._create_stripe_invoice(
            tenant_id=tenant_id,
            amount_credits=total_amount_credits,
            description=f'{tenant_name} - Invoice for {period_start.strftime("%B %Y")}',
            customer_email=customer_email,
            customer_name=tenant_name,
            line_items=stripe_line_items,
            metadata={
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'invoice_type': 'monthly_billing'
            },
            currency=currency
        )

        # Build database line items for transaction function
        db_line_items = []

        if total_credits_allocated > 0:
            db_line_items.append({
                'item_type': 'credit_allocation',
                'description': f'Credits allocated during {period_start.strftime("%B %Y")}',
                'quantity': 1,
                'unit_price_credits': total_credits_allocated,
                'total_price_credits': total_credits_allocated,
                'metadata': {
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat()
                }
            })

        if admin_seat_charges > 0:
            db_line_items.append({
                'item_type': 'admin_seat',
                'description': f'Admin seat charges ({admin_seats_count} seats × {admin_seat_price} credits)',
                'quantity': admin_seats_count,
                'unit_price_credits': admin_seat_price,
                'total_price_credits': admin_seat_charges,
                'metadata': {
                    'admin_seats_count': admin_seats_count,
                    'seat_price': admin_seat_price
                }
            })

        # Now save to database atomically using raw SQL transaction
        with self.transaction() as conn:
            invoice = create_invoice_with_stripe_atomic(
                conn=conn,
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                credits_allocated=total_credits_allocated,
                admin_seat_charges=admin_seat_charges,
                total_amount_credits=total_amount_credits,
                admin_seats_count=admin_seats_count,
                members_count=members_count,
                stripe_invoice_id=stripe_invoice['stripe_invoice_id'],
                stripe_invoice_number=stripe_invoice['stripe_invoice_number'],
                stripe_hosted_url=stripe_invoice['hosted_invoice_url'],
                stripe_pdf_url=stripe_invoice['invoice_pdf'],
                tenant_name=tenant_name,
                line_items=db_line_items
            )

            # Mark credit allocations as invoiced (prevents double-billing)
            if allocation_ids:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE organization_credit_allocations
                    SET invoice_id = %s, invoiced_at = NOW()
                    WHERE id = ANY(ARRAY(
                        SELECT unnest(%s::text[])::uuid
                    ))
                """, (invoice['id'], allocation_ids))
                logger.info(f"Marked {len(allocation_ids)} credit allocations as invoiced with invoice {invoice['invoice_number']}")

        logger.info(
            f"Created invoice {invoice['invoice_number']} with Stripe invoice "
            f"{stripe_invoice['stripe_invoice_number']} for tenant {tenant_id}"
        )

        # Mark allocations as invoiced (prevents double-billing)
        if allocation_ids:
            now = datetime.now(timezone.utc)
            self.supabase.table('organization_credit_allocations') \
                .update({
                    'invoice_id': invoice['id'],
                    'invoiced_at': now.isoformat()
                }) \
                .in_('id', allocation_ids) \
                .execute()
            logger.info(f"Marked {len(allocation_ids)} credit allocations as invoiced for invoice {invoice['invoice_number']}")

        # Add Stripe URL to return data
        invoice['stripe_hosted_invoice_url'] = stripe_invoice['hosted_invoice_url']
        invoice['stripe_invoice_pdf'] = stripe_invoice['invoice_pdf']

        # Send invoice email notification
        if customer_email:
            try:
                email_service.send_invoice_email(
                    to_email=customer_email,
                    org_name=tenant_name,
                    invoice_number=invoice['invoice_number'],
                    invoice_amount=float(total_amount_credits),
                    due_date=invoice['due_date'],
                    payment_link=stripe_invoice['hosted_invoice_url']
                )
                logger.info(f"Sent invoice email to {customer_email} for invoice {invoice['invoice_number']}")
            except Exception as e:
                logger.error(f"Failed to send invoice email: {e}", exc_info=True)
                # Don't fail the invoice generation if email fails

        return invoice

    def charge_prepay_admin_seats(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """
        Charge monthly admin seat fees for a prepay_org organization.

        For prepay_org:
        - If sufficient credits: Deduct credits directly using FIFO strategy (atomic transaction)
        - If insufficient credits: Generate invoice for FULL amount (no credit deduction)

        Args:
            tenant_id: Organization tenant ID
            period_start: Start of billing period
            period_end: End of billing period

        Returns:
            Dict containing billing result with status and details

        Raises:
            BillingError: If billing fails
        """
        logger.info(f"Charging admin seats for prepay org {tenant_id}, period {period_start} to {period_end}")

        # Verify organization is prepay_org (READ using Supabase - outside transaction)
        org_config_response = self.supabase.table('organization_billing_config') \
            .select('organization_type, billing_settings, tenants!inner(name)') \
            .eq('tenant_id', tenant_id) \
            .single() \
            .execute()

        if not org_config_response.data:
            raise BillingError(f"No billing config found for tenant {tenant_id}")

        if org_config_response.data['organization_type'] != 'prepay_org':
            raise BillingError(f"Tenant {tenant_id} is not a prepay organization")

        tenant_name = org_config_response.data['tenants']['name']
        billing_settings = org_config_response.data.get('billing_settings') or {}
        currency = billing_settings.get('currency', 'USD')

        # Skip if this period's admin seat billing was already processed
        existing_billing_response = self.supabase.table('admin_seat_billing_history') \
            .select('id, status, invoice_id, admin_seats_count, seat_price_credits, total_charged_credits, deducted_at, created_at') \
            .eq('tenant_id', tenant_id) \
            .eq('billing_period_start', period_start.isoformat()) \
            .eq('billing_period_end', period_end.isoformat()) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        if existing_billing_response.data:
            existing_billing = existing_billing_response.data[0]
            existing_status = existing_billing.get('status')
            if existing_status in ['completed', 'charged']:
                logger.info(
                    f"Admin seat billing already completed for tenant {tenant_id}, "
                    f"period {period_start} to {period_end}"
                )
                return {
                    'success': True,
                    'already_processed': True,
                    'payment_method': 'already_paid',
                    'admin_seats_count': existing_billing.get('admin_seats_count', 0),
                    'seat_price': existing_billing.get('seat_price_credits'),
                    'total_charged': existing_billing.get('total_charged_credits'),
                    'deducted_at': existing_billing.get('deducted_at'),
                    'message': 'Admin seats already paid for this period'
                }

            if existing_status in ['invoiced', 'pending'] and existing_billing.get('invoice_id'):
                invoice_response = self.supabase.table('invoices') \
                    .select('id, invoice_number, status, stripe_invoice_id, metadata, total_amount_credits, issued_at, due_date') \
                    .eq('id', existing_billing['invoice_id']) \
                    .single() \
                    .execute()

                if invoice_response.data:
                    invoice = invoice_response.data
                    metadata = invoice.get('metadata') or {}
                    if invoice.get('status') == 'paid':
                        logger.info(
                            f"Admin seat invoice already paid for tenant {tenant_id}, "
                            f"period {period_start} to {period_end}"
                        )
                        return {
                            'success': True,
                            'already_processed': True,
                            'payment_method': 'already_paid',
                            'admin_seats_count': existing_billing.get('admin_seats_count', 0),
                            'seat_price': existing_billing.get('seat_price_credits'),
                            'total_charged': existing_billing.get('total_charged_credits'),
                            'invoice_id': invoice.get('id'),
                            'invoice_number': invoice.get('invoice_number'),
                            'stripe_hosted_invoice_url': metadata.get('stripe_hosted_url'),
                            'stripe_invoice_pdf': metadata.get('stripe_pdf_url'),
                            'message': 'Admin seat invoice already paid for this period'
                        }

                    logger.info(
                        f"Admin seat invoice already exists for tenant {tenant_id}, "
                        f"period {period_start} to {period_end}"
                    )
                    return {
                        'success': True,
                        'already_processed': True,
                        'payment_method': 'already_invoiced',
                        'admin_seats_count': existing_billing.get('admin_seats_count', 0),
                        'seat_price': existing_billing.get('seat_price_credits'),
                        'total_charged': existing_billing.get('total_charged_credits'),
                        'invoice_id': invoice.get('id'),
                        'invoice_number': invoice.get('invoice_number'),
                        'stripe_hosted_invoice_url': metadata.get('stripe_hosted_url'),
                        'stripe_invoice_pdf': metadata.get('stripe_pdf_url'),
                        'invoice_status': invoice.get('status'),
                        'message': 'Admin seat invoice already exists for this period'
                    }

        # Get pricing
        pricing = self.get_pricing_config()
        seat_price = pricing['admin_seat_price_credits']

        # Count admin seats
        admin_seats_response = self.supabase.table('tenant_memberships') \
            .select('id', count='exact') \
            .eq('tenant_id', tenant_id) \
            .eq('role', 'admin') \
            .eq('is_active', True) \
            .execute()

        admin_seats_count = admin_seats_response.count or 0
        total_charge = admin_seats_count * seat_price

        if admin_seats_count == 0:
            logger.info(f"No admin seats to charge for tenant {tenant_id}")
            return {
                'success': True,
                'admin_seats_count': 0,
                'total_charged': 0,
                'payment_method': 'none',
                'message': 'No admin seats to charge'
            }

        # Get available credits
        available_credits = self._get_available_credits(tenant_id)

        # PATH 1: Sufficient credits - deduct directly using atomic transaction
        if available_credits >= total_charge:
            logger.info(f"Sufficient credits available ({available_credits} >= {total_charge}), deducting from balance")

            with self.transaction() as conn:
                # Consume credits atomically using FIFO
                consumption_id = consume_credits_fifo_atomic(
                    conn=conn,
                    tenant_id=tenant_id,
                    amount=total_charge,
                    reason=f'Admin seat billing for {period_start.strftime("%B %Y")} ({admin_seats_count} seats)'
                )

                # Record in billing history (using raw SQL in same transaction)
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO admin_seat_billing_history (
                            tenant_id, billing_period_start, billing_period_end,
                            admin_seats_count, seat_price_credits, total_charged_credits,
                            consumption_id, deducted_at, status, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
                    """, (
                        tenant_id,
                        period_start,
                        period_end,
                        admin_seats_count,
                        seat_price,
                        total_charge,
                        consumption_id,
                        'completed',
                        psycopg2.extras.Json({
                            'processed_by': 'billing_service',
                            'processed_at': self._now().isoformat()
                        })
                    ))
                finally:
                    cursor.close()

            logger.info(f"Successfully charged {total_charge} credits for {admin_seats_count} admin seats (tenant {tenant_id})")

            return {
                'success': True,
                'admin_seats_count': admin_seats_count,
                'seat_price': seat_price,
                'total_charged': total_charge,
                'available_credits_remaining': available_credits - total_charge,
                'payment_method': 'credit_deduction',
                'consumption_id': consumption_id
            }

        # PATH 2: Insufficient credits - generate invoice for FULL amount (no credit deduction)
        else:
            logger.warning(
                f"Insufficient credits for tenant {tenant_id}: needed {total_charge}, available {available_credits}. "
                f"Generating invoice for FULL amount with Stripe payment."
            )

            # Get org owner email for Stripe
            owner_response = self.supabase.table('tenant_memberships') \
                .select('user_profiles!inner(email)') \
                .eq('tenant_id', tenant_id) \
                .eq('role', 'owner') \
                .eq('is_active', True) \
                .limit(1) \
                .execute()

            customer_email = owner_response.data[0]['user_profiles']['email'] if owner_response.data else None

            # Get exchange rate to convert credits to fiat amount
            from ..payment_v2_stripe.service import PaymentService
            payment_service = PaymentService()
            rate = payment_service.get_credits_per_unit(currency)

            # Calculate fiat amount from credits
            charge_amount = float(Decimal(str(total_charge)) / Decimal(str(rate)))

            # Build Stripe line items
            stripe_line_items = [{
                'description': f'Admin seat charges ({admin_seats_count} seats × {seat_price} credits) - Insufficient prepaid balance',
                'amount_cents': int(charge_amount * 100),
                'metadata': {
                    'item_type': 'admin_seat',
                    'admin_seats_count': admin_seats_count,
                    'seat_price': seat_price,
                    'insufficient_credits': True,
                    'credits_available': available_credits,
                    'credits_needed': total_charge
                }
            }]

            # Create Stripe invoice FIRST (outside transaction)
            stripe_invoice = self._create_stripe_invoice(
                tenant_id=tenant_id,
                amount_credits=total_charge,
                description=f'{tenant_name} - Admin Seats ({admin_seats_count} seats)',
                customer_email=customer_email,
                customer_name=tenant_name,
                line_items=stripe_line_items,
                metadata={
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'invoice_type': 'insufficient_credits_admin_seats',
                    'credits_available': available_credits,
                    'credits_needed': total_charge
                },
                currency=currency
            )

            # Build database line items
            db_line_items = [{
                'item_type': 'admin_seat',
                'description': f'Admin seat charges ({admin_seats_count} seats × {seat_price} credits) - Insufficient prepaid balance',
                'quantity': admin_seats_count,
                'unit_price_credits': seat_price,
                'total_price_credits': total_charge,
                'metadata': {
                    'admin_seats_count': admin_seats_count,
                    'seat_price': seat_price,
                    'insufficient_credits': True,
                    'credits_available': available_credits,
                    'credits_needed': total_charge
                }
            }]

            # Save to database atomically
            with self.transaction() as conn:
                invoice = create_invoice_with_stripe_atomic(
                    conn=conn,
                    tenant_id=tenant_id,
                    period_start=period_start,
                    period_end=period_end,
                    credits_allocated=0,  # No credits allocated, just admin seat charges
                    admin_seat_charges=total_charge,
                    total_amount_credits=total_charge,
                    admin_seats_count=admin_seats_count,
                    members_count=0,
                    stripe_invoice_id=stripe_invoice['stripe_invoice_id'],
                    stripe_invoice_number=stripe_invoice['stripe_invoice_number'],
                    stripe_hosted_url=stripe_invoice['hosted_invoice_url'],
                    stripe_pdf_url=stripe_invoice['invoice_pdf'],
                    tenant_name=tenant_name,
                    line_items=db_line_items
                )

                invoice_id = invoice['id']

                # Record in billing history (same transaction)
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO admin_seat_billing_history (
                            tenant_id, billing_period_start, billing_period_end,
                            admin_seats_count, seat_price_credits, total_charged_credits,
                            invoice_id, status, error_message, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """, (
                        tenant_id,
                        period_start,
                        period_end,
                        admin_seats_count,
                        seat_price,
                        total_charge,
                        invoice_id,
                        'invoiced',
                        f'Insufficient credits: {available_credits} < {total_charge}',
                        psycopg2.extras.Json({
                            'processed_by': 'billing_service',
                            'processed_at': self._now().isoformat(),
                            'credits_available': available_credits,
                            'credits_needed': total_charge
                        })
                    ))
                finally:
                    cursor.close()

            logger.info(
                f"Created invoice {invoice['invoice_number']} with Stripe invoice "
                f"{stripe_invoice['stripe_invoice_number']} for admin seats due to insufficient credits (tenant {tenant_id})"
            )

            # Send email notifications for insufficient credits scenario
            if customer_email:
                try:
                    # Send invoice email
                    email_service.send_invoice_email(
                        to_email=customer_email,
                        org_name=tenant_name,
                        invoice_number=invoice['invoice_number'],
                        invoice_amount=float(total_charge),
                        due_date=invoice['due_date'],
                        payment_link=stripe_invoice['hosted_invoice_url']
                    )
                    logger.info(f"Sent invoice email to {customer_email} for invoice {invoice['invoice_number']}")

                    # Send low credit warning email
                    # Get frontend URL for purchase link
                    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
                    purchase_link = f"{frontend_url}/billing/bulk-purchase?tenant_id={tenant_id}"

                    email_service.send_low_credit_warning_email(
                        to_email=customer_email,
                        org_name=tenant_name,
                        current_balance=available_credits,
                        required_credits=total_charge,
                        admin_seats_count=admin_seats_count,
                        purchase_link=purchase_link
                    )
                    logger.info(f"Sent low credit warning email to {customer_email} for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send email notifications: {e}", exc_info=True)
                    # Don't fail the billing operation if email fails

            return {
                'success': True,
                'admin_seats_count': admin_seats_count,
                'seat_price': seat_price,
                'total_charged': total_charge,
                'available_credits': available_credits,
                'payment_method': 'invoice',
                'invoice_id': invoice_id,
                'invoice_number': invoice['invoice_number'],
                'stripe_hosted_invoice_url': stripe_invoice['hosted_invoice_url'],
                'stripe_invoice_pdf': stripe_invoice['invoice_pdf'],
                'message': 'Insufficient credits - invoice generated with Stripe payment link'
            }

    def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_method: str,
        payment_reference: Optional[str] = None,
        payment_notes: Optional[str] = None,
        marked_by: str = None
    ) -> Dict[str, Any]:
        """
        Manually mark an invoice as paid (for non-Stripe payments).

        Args:
            invoice_id: Invoice ID
            payment_method: Payment method (manual, bank_transfer, other)
            payment_reference: Optional payment reference/transaction ID
            payment_notes: Optional notes about the payment
            marked_by: User ID who marked the invoice as paid

        Returns:
            Dict containing updated invoice

        Raises:
            InvoiceNotFoundError: If invoice not found
            BillingError: If invoice cannot be marked as paid
        """
        logger.info(f"Marking invoice {invoice_id} as paid, method={payment_method}")

        # Get invoice
        invoice_response = self.supabase.table('invoices') \
            .select('*') \
            .eq('id', invoice_id) \
            .single() \
            .execute()

        if not invoice_response.data:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

        invoice = invoice_response.data

        if invoice['status'] == 'paid':
            logger.warning(f"Invoice {invoice_id} is already marked as paid")
            return invoice

        if invoice['status'] not in ['pending', 'overdue']:
            raise BillingError(f"Invoice {invoice_id} has status '{invoice['status']}' and cannot be marked as paid")

        # Update invoice
        now = self._now()
        update_data = {
            'status': 'paid',
            'paid_at': now.isoformat(),
            'payment_method': payment_method,
            'payment_reference': payment_reference,
            'payment_notes': payment_notes,
            'marked_paid_by': marked_by,
            'marked_paid_at': now.isoformat(),
            'updated_at': now.isoformat()
        }

        updated_response = self.supabase.table('invoices') \
            .update(update_data) \
            .eq('id', invoice_id) \
            .execute()

        if not updated_response.data:
            raise BillingError(f"Failed to update invoice {invoice_id}")

        logger.info(f"Invoice {invoice['invoice_number']} marked as paid")

        return updated_response.data[0]

    def _get_available_credits(self, tenant_id: str) -> int:
        """Calculate total available credits for a tenant"""
        now = self._now()
        now_iso = now.isoformat()

        # Note: Removed .or_() as Supabase Python client doesn't support it
        # Expiration filtering is done in Python below
        response = self.supabase.table('credit_lots') \
            .select('credit_amount, expires_at') \
            .eq('tenant_id', tenant_id) \
            .eq('is_active', True) \
            .execute()

        if not response.data:
            return 0
        
        # Filter: expires_at is null OR expires_at > now
        total = 0
        for lot in response.data:
            expires_at = lot.get('expires_at')
            if expires_at is None or str(expires_at) > now_iso:
                total += lot['credit_amount']
        return total
