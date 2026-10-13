import json
from decimal import Decimal
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, UserIntegration, Invoice, Reminder, AuditLog
from app.schemas import (
    IntegrationConfigUpdate,
    IntegrationResponse,
    WebhookTestRequest,
)
from app.config import settings
from app.services.integrations.stripe_service import verify_stripe_webhook
from app.services.integrations.webhook_service import _send_slack, _send_discord, _send_generic

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("", response_model=List[IntegrationResponse])
def get_user_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(UserIntegration)
        .filter(UserIntegration.user_id == current_user.id)
        .all()
    )


@router.post("", response_model=IntegrationResponse)
def save_user_integration(
    data: IntegrationConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(UserIntegration)
        .filter(
            UserIntegration.user_id == current_user.id,
            UserIntegration.service_name == data.service_name,
        )
        .first()
    )
    if existing:
        existing.is_active = data.is_active
        existing.config_json = json.dumps(data.config_data)
        db.commit()
        db.refresh(existing)
        return existing

    new_integration = UserIntegration(
        user_id=current_user.id,
        service_name=data.service_name,
        is_active=data.is_active,
        config_json=json.dumps(data.config_data),
    )
    db.add(new_integration)
    db.commit()
    db.refresh(new_integration)
    return new_integration


@router.post("/test-webhook")
def test_webhook(
    req: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
):
    payload = {
        "message": f"Test notification from Invoice Chaser by {current_user.business_name or current_user.email}",
        "status": "connected",
        "service": req.service,
    }
    destinations = {
        "slack": settings.slack_webhook_url,
        "discord": settings.discord_webhook_url,
        "generic": settings.generic_webhook_url,
    }
    if req.service not in destinations:
        raise HTTPException(status_code=422, detail="Unsupported webhook service")
    if not destinations[req.service] or req.webhook_url != destinations[req.service]:
        raise HTTPException(status_code=400, detail="Webhook URL must match the configured server destination")
    if req.service == "slack":
        _send_slack("webhook.test", payload)
    elif req.service == "discord":
        _send_discord("webhook.test", payload)
    else:
        _send_generic("webhook.test", payload)
    return {"status": "dispatched", "message": "Test request submitted to configured destination"}


@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Handle incoming Stripe webhook to automatically mark invoice paid."""
    body = await request.body()
    event = verify_stripe_webhook(body, stripe_signature)
    if not event:
        if settings.stripe_webhook_secret:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")
        return {"status": "unverified_or_skipped"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("payment_status") != "paid":
            return {"status": "ignored", "reason": "payment_not_confirmed"}
        invoice_id_str = session.get("client_reference_id") or (session.get("metadata") or {}).get("invoice_id")
        try:
            inv_id = int(invoice_id_str)
        except (ValueError, TypeError):
            return {"status": "ignored", "reason": "invoice_id_missing"}
        invoice = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not invoice:
            return {"status": "ignored", "reason": "invoice_not_found"}
        # Do not trust reference IDs alone: the signed event must also match the debt.
        expected_minor = int(Decimal(invoice.amount) * 100)
        if session.get("amount_total") != expected_minor or (
            (session.get("currency") or "").upper() != (invoice.currency or "").upper()
        ):
            return {"status": "ignored", "reason": "payment_mismatch"}
        if invoice.status != "paid":
            invoice.status = "paid"
            invoice.paid_date = date.today()
            for rem in invoice.reminders:
                if rem.sent_at is None:
                    rem.status = "cancelled"
            db.commit()
    return {"status": "handled"}
