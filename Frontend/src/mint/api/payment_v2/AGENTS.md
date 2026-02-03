# Payment System Architecture

## Purpose
The `src/mint/api/payment_v2` module manages financial transactions, specifically handling **Flutterwave** integration (Nigerian market focus). Note that Stripe logic resides in a separate `payment_v2_stripe` module.

## Directory Structure
- `endpoints.py`: Routes for initializing payments and verifying transactions.
- `service.py`: Business logic interacting with the Payment Gateway APIs.
- `models.py`: Pydantic models for payment requests and webhooks.

## Key Components
- **Payment Initialization:** Creates a transaction reference and returns a checkout URL.
- **Webhook Handler:** Securely verifies incoming webhooks to update transaction status (Success/Failed).
- **Credit Allocation:** Upon successful payment, this service triggers the **Credit Service** to add credits to the user's wallet.

## Integration
- **Input:** User selects a credit package.
- **Process:** Payment Gateway -> Webhook -> Backend Verification.
- **Output:** Updates `user_credits` table and logs transaction history.
