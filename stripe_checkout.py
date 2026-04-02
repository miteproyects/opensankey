"""
QuarterCharts – Stripe Checkout Integration
============================================
Handles Stripe Checkout Sessions (redirect flow) and webhook processing.

Setup:
  1. Set environment variables:
     - STRIPE_SECRET_KEY      (sk_live_... or sk_test_...)
     - STRIPE_WEBHOOK_SECRET  (whsec_...)
  2. In Stripe Dashboard, create Products + Prices matching your DB plans.
  3. Copy the price IDs into the NSFE Pricing admin tab.
  4. Set up a webhook endpoint pointing to /api/stripe-webhook
     with events: checkout.session.completed, customer.subscription.updated,
                  customer.subscription.deleted

Architecture (Stripe best practices):
  - Stripe-hosted Checkout page (redirect, not embedded)
  - Prices are created in Stripe Dashboard, IDs stored in our DB
  - Webhook verifies signature before processing
  - Subscriptions table tracks status locally
"""

import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SITE_URL = os.environ.get("SITE_URL", "https://quartercharts.com")


def is_stripe_configured() -> bool:
    """Check if Stripe keys are set."""
    return bool(STRIPE_SECRET_KEY)


def _get_stripe():
    """Lazy-import and configure stripe."""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


# ── Checkout Session ────────────────────────────────────────────────────

def create_checkout_session(
    user_id: int,
    user_email: str,
    price_id: str,
    plan_slug: str,
    ticker: str = "AAPL",
) -> str | None:
    """
    Create a Stripe Checkout Session and return the URL to redirect to.

    Args:
        user_id:    Our internal user ID (stored in metadata)
        user_email: Pre-fill the Checkout email field
        price_id:   Stripe Price ID (price_xxx) from the plan
        plan_slug:  Our plan slug for success page routing
        ticker:     Current ticker for redirect URLs

    Returns:
        Checkout session URL string, or None on failure.
    """
    if not is_stripe_configured():
        logger.warning("Stripe not configured – cannot create checkout session")
        return None

    try:
        stripe = _get_stripe()

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{SITE_URL}/?page=dashboard&ticker={ticker}&checkout=success&plan={plan_slug}",
            cancel_url=f"{SITE_URL}/?page=pricing&ticker={ticker}&checkout=cancelled",
            metadata={
                "user_id": str(user_id),
                "plan_slug": plan_slug,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user_id),
                    "plan_slug": plan_slug,
                },
            },
            allow_promotion_codes=True,
        )

        logger.info(f"Checkout session created for user {user_id}, plan {plan_slug}")
        return session.url

    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return None


# ── Webhook Processing ──────────────────────────────────────────────────

def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Verify and process a Stripe webhook event.

    Args:
        payload:    Raw request body bytes
        sig_header: Stripe-Signature header value

    Returns:
        Dict with 'success' bool and 'message' string.
    """
    if not STRIPE_WEBHOOK_SECRET:
        return {"success": False, "message": "Webhook secret not configured"}

    try:
        stripe = _get_stripe()
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook signature verification failed")
        return {"success": False, "message": "Invalid signature"}
    except Exception as e:
        logger.warning(f"Webhook error: {e}")
        return {"success": False, "message": str(e)}

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Processing webhook: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    else:
        logger.info(f"Unhandled event type: {event_type}")

    return {"success": True, "message": f"Processed {event_type}"}


def _handle_checkout_completed(session: dict):
    """Process successful checkout – create/update local subscription record."""
    from database import get_connection

    user_id = session.get("metadata", {}).get("user_id")
    plan_slug = session.get("metadata", {}).get("plan_slug")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not user_id or not subscription_id:
        logger.warning("Checkout completed but missing user_id or subscription_id")
        return

    try:
        with get_connection() as conn:
            if conn is None:
                logger.error("No DB connection for checkout handler")
                return
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO subscriptions (user_id, plan_slug, stripe_subscription_id,
                                               stripe_customer_id, status, current_period_start,
                                               current_period_end)
                    VALUES (%s, %s, %s, %s, 'active', NOW(), NOW() + INTERVAL '30 days')
                    ON CONFLICT (user_id) DO UPDATE SET
                        plan_slug = EXCLUDED.plan_slug,
                        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                        stripe_customer_id = EXCLUDED.stripe_customer_id,
                        status = 'active',
                        updated_at = NOW()
                """, (int(user_id), plan_slug, subscription_id, customer_id))
        logger.info(f"Subscription created for user {user_id}, plan {plan_slug}")
    except Exception as e:
        logger.error(f"Failed to save subscription: {e}")


def _handle_subscription_updated(subscription: dict):
    """Update local subscription when Stripe sub changes (upgrade/downgrade/renewal)."""
    from database import get_connection

    sub_id = subscription.get("id")
    status = subscription.get("status")  # active, past_due, canceled, etc.
    period_start = subscription.get("current_period_start")
    period_end = subscription.get("current_period_end")

    try:
        with get_connection() as conn:
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subscriptions
                    SET status = %s,
                        current_period_start = to_timestamp(%s),
                        current_period_end = to_timestamp(%s),
                        updated_at = NOW()
                    WHERE stripe_subscription_id = %s
                """, (status, period_start, period_end, sub_id))
        logger.info(f"Subscription {sub_id} updated to status: {status}")
    except Exception as e:
        logger.error(f"Failed to update subscription: {e}")


def _handle_subscription_deleted(subscription: dict):
    """Mark subscription as canceled when deleted in Stripe."""
    from database import get_connection

    sub_id = subscription.get("id")

    try:
        with get_connection() as conn:
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE subscriptions
                    SET status = 'canceled', cancel_at = NOW(), updated_at = NOW()
                    WHERE stripe_subscription_id = %s
                """, (sub_id,))
        logger.info(f"Subscription {sub_id} canceled")
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")


# ── Customer Portal ─────────────────────────────────────────────────────

def create_portal_session(stripe_customer_id: str, ticker: str = "AAPL") -> str | None:
    """
    Create a Stripe Customer Portal session for managing subscription.
    Returns the portal URL, or None on failure.
    """
    if not is_stripe_configured():
        return None

    try:
        stripe = _get_stripe()
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{SITE_URL}/?page=dashboard&ticker={ticker}",
        )
        return session.url
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        return None
