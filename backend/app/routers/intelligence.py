from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Invoice, PaymentPlan
from app.schemas import (
    RiskAssessmentResponse,
    ToneEscalationRequest,
    ToneEscalationResponse,
    DisputeDraftRequest,
    DisputeDraftResponse,
    PaymentPlanCreate,
    PaymentPlanResponse,
)
from app.services.intelligent_engine import (
    calculate_invoice_risk,
    generate_ai_reminder_message,
    generate_dispute_response,
)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/invoices/{invoice_id}/risk", response_model=RiskAssessmentResponse)
def get_invoice_risk(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = invoice.client
    risk_info = calculate_invoice_risk(invoice, client)
    return risk_info


@router.post("/escalate-tone", response_model=ToneEscalationResponse)
def escalate_tone(
    req: ToneEscalationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == req.invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    days_offset = (invoice.due_date - invoice.issued_date).days
    subject, body = generate_ai_reminder_message(
        business_name=current_user.business_name or "Our Company",
        client_name=invoice.client.name,
        client_notes=invoice.client.notes,
        invoice_number=invoice.invoice_number,
        amount=float(invoice.amount),
        currency=invoice.currency or "USD",
        description=invoice.description,
        due_date_str=invoice.due_date.strftime("%B %d, %Y"),
        days_offset=days_offset,
        tone=req.target_tone,
        custom_instruction=req.custom_instruction,
    )

    # Calculate projected response rate based on tone
    rate_map = {
        "friendly": 72.5,
        "professional": 65.0,
        "firm": 58.0,
        "urgent": 49.0,
        "final": 38.0,
        "legal": 29.0,
    }

    return ToneEscalationResponse(
        tone=req.target_tone,
        subject=subject,
        body=body,
        recommended_send_hour_utc=14,  # Optimal 9am EST / 2pm UTC
        projected_response_rate_pct=rate_map.get(req.target_tone.lower(), 55.0),
    )


@router.post("/draft-dispute-reply", response_model=DisputeDraftResponse)
def draft_dispute_reply(
    req: DisputeDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == req.invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    result = generate_dispute_response(invoice, invoice.client, req.client_excuse)
    return result


@router.post("/invoices/{invoice_id}/payment-plan", response_model=PaymentPlanResponse)
def create_payment_plan(
    invoice_id: int,
    plan_data: PaymentPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    total = invoice.amount
    count = plan_data.installments_count
    installment_amount = Decimal(round(float(total) / count, 2))

    plan = PaymentPlan(
        invoice_id=invoice.id,
        total_amount=total,
        installments_count=count,
        installment_amount=installment_amount,
        frequency_days=plan_data.frequency_days,
        status="proposed",
        notes=plan_data.notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/invoices/{invoice_id}/payment-plans", response_model=List[PaymentPlanResponse])
def get_payment_plans(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice.payment_plans
