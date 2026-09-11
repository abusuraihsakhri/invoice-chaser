import json
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
    if req.service == "slack":
        _send_slack("webhook.test", payload)
    elif req.service == "discord":
        _send_discord("webhook.test", payload)
    else:
        _send_generic("webhook.test", payload)

    return {"status": "success", "message": f"Sent test payload to {req.service}"}


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
        invoice_id_str = session.get("client_reference_id") or session.get("metadata", {}).get("invoice_id")
        if invoice_id_str:
            try:
                inv_id = int(invoice_id_str)
                invoice = db.query(Invoice).filter(Invoice.id == inv_id).first()
                if invoice and invoice.status != "paid":
                    invoice.status = "paid"
                    invoice.paid_date = date.today()
                    # Cancel pending reminders
                    for rem in invoice.reminders:
                        if rem.sent_at is None:
                            rem.status = "cancelled"
                    db.commit()
            except Exception:
                pass

    return {"status": "handled"}
