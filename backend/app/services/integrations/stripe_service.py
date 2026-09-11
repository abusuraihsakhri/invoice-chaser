import logging
from typing import Optional, Dict, Any
try:
    import stripe
except ImportError:
    stripe = None

from app.config import settings

logger = logging.getLogger("invoice_chaser.stripe")


def get_stripe_client():
    if stripe is not None and settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
    return stripe


def create_invoice_checkout_session(
    invoice_id: int,
    invoice_number: str,
    amount: float,
    currency: str,
    client_email: str,
    business_name: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, str]:
    """Create a Stripe Checkout Session for an invoice."""
    client = get_stripe_client()
    if client is None or not settings.stripe_secret_key:
        # Generate simulated sandbox payment URL for test/demo mode
        demo_url = f"{settings.frontend_url}/invoices?mock_paid_invoice_id={invoice_id}"
        return {
            "checkout_url": demo_url,
            "session_id": f"demo_sess_{invoice_id}",
        }

    try:
        frontend_base = settings.frontend_url.rstrip("/")
        s_url = success_url or f"{frontend_base}/invoices?session_id={{CHECKOUT_SESSION_ID}}&paid=1"
        c_url = cancel_url or f"{frontend_base}/invoices?cancelled=1"

        # Amount in smallest currency unit (cents)
        unit_amount = int(round(amount * 100))

        session = client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": f"Invoice {invoice_number}",
                        "description": f"Payment to {business_name}",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            customer_email=client_email,
            client_reference_id=str(invoice_id),
            metadata={"invoice_id": str(invoice_id), "invoice_number": invoice_number},
            success_url=s_url,
            cancel_url=c_url,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }
    except Exception as exc:
        logger.error("Failed to create Stripe checkout session: %s", exc)
        raise exc


def verify_stripe_webhook(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    """Verify webhook signature from Stripe."""
    if stripe is None or not settings.stripe_webhook_secret:
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return event
    except Exception as exc:
        logger.warning("Stripe signature verification failed: %s", exc)
        return None
