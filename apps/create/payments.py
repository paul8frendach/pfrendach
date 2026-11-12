"""
Stripe for Oasis Media Visions — payments straight into Paul's own account.

Hosted Stripe Checkout only: card data never touches this site, so there is no
PCI surface here. Keys come from the environment; with none set the booking
buttons simply don't render and the page falls back to request-a-quote, so a
missing key degrades to the old behaviour instead of a 500.

Test mode and live mode are the same code — only the keys differ.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import stripe
except ModuleNotFoundError:  # SDK not installed yet; feature stays dark
    stripe = None


def configured() -> bool:
    """True only when we can actually talk to Stripe."""
    return bool(stripe and settings.STRIPE_SECRET_KEY)


def _client():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(*, payment, success_url: str, cancel_url: str, description: str):
    """
    Create a hosted Checkout session for one Payment and return it.
    Raises if Stripe is not configured — callers check configured() first.
    """
    if not configured():
        raise RuntimeError("Stripe is not configured")
    s = _client()
    session = s.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": settings.STRIPE_CURRENCY,
                "product_data": {"name": description},
                "unit_amount": payment.amount_cents,
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "payment_id": str(payment.pk),
            "kind": payment.kind,
            "package": payment.package.slug if payment.package_id else "",
            "commission_id": str(payment.commission_id or ""),
        },
        payment_intent_data={"description": description},
        billing_address_collection="auto",
        allow_promotion_codes=False,
    )
    return session


def verify_webhook(payload: bytes, sig_header: str):
    """Verify and return a Stripe event, or raise on a bad signature."""
    if not stripe:
        raise RuntimeError("Stripe SDK not installed")
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
