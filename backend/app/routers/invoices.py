from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Invoice, Client, Reminder, AuditLog
from app.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    StripeCheckoutResponse,
)
from app.services.ai_reminder import generate_reminder_content
from app.services.integrations.pdf_service import generate_invoice_pdf
from app.services.integrations.stripe_service import create_invoice_checkout_session
from app.services.integrations.webhook_service import dispatch_event
from app.services.integrations.export_service import export_invoices_to_csv

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def generate_invoice_number(db: Session, user: User) -> str:
    """Generate next sequential invoice number with customizable prefix: INV-001, etc."""
    prefix = user.invoice_prefix or "INV"
    last = (
        db.query(Invoice)
        .filter(Invoice.user_id == user.id)
        .order_by(Invoice.id.desc())
        .first()
    )
    if last and "-" in last.invoice_number:
        try:
            num = int(last.invoice_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"{prefix}-{num:03d}"


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    return query.order_by(Invoice.created_at.desc()).all()


@router.get("/export/csv")
def export_invoices_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).order_by(Invoice.created_at.desc()).all()
    csv_data = export_invoices_to_csv(invoices)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="invoices_export.csv"'},
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
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
    return invoice


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
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

    pdf_bytes = generate_invoice_pdf(invoice, current_user, invoice.client)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        },
    )


@router.post("", response_model=InvoiceResponse)
def create_invoice(
    invoice_data: InvoiceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == invoice_data.client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    invoice_num = generate_invoice_number(db, current_user)
    currency = invoice_data.currency or current_user.currency or "USD"

    # Create invoice
    invoice = Invoice(
        user_id=current_user.id,
        client_id=invoice_data.client_id,
        invoice_number=invoice_num,
        amount=invoice_data.amount,
        currency=currency,
        description=invoice_data.description,
        status="sent",
        payment_url=invoice_data.payment_url,
        issued_date=invoice_data.issued_date,
        due_date=invoice_data.due_date,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Automatically generate Stripe payment link if not provided
    if not invoice.payment_url:
        try:
            stripe_res = create_invoice_checkout_session(
                invoice_id=invoice.id,
                invoice_number=invoice.invoice_number,
                amount=float(invoice.amount),
                currency=currency,
                client_email=client.email,
                business_name=current_user.business_name or "Invoice Chaser",
            )
            invoice.payment_url = stripe_res["checkout_url"]
            db.commit()
            db.refresh(invoice)
        except Exception:
            pass

    # Auto-schedule reminders with intelligent engine
    generate_reminder_content(db, invoice, current_user, client)

    # Audit log & Webhook
    audit = AuditLog(
        user_id=current_user.id,
        action="INVOICE_CREATED",
        ip_address=request.client.host if request.client else None,
        details=f"Created invoice {invoice.invoice_number} for {client.name} ({currency} {invoice.amount})",
    )
    db.add(audit)
    db.commit()

    dispatch_event("invoice.created", {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "client_name": client.name,
        "amount": float(invoice.amount),
        "currency": currency,
        "due_date": str(invoice.due_date),
    })

    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/payment-link", response_model=StripeCheckoutResponse)
def generate_payment_link(
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

    res = create_invoice_checkout_session(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        amount=float(invoice.amount),
        currency=invoice.currency or "USD",
        client_email=invoice.client.email,
        business_name=current_user.business_name or "Invoice Chaser",
    )
    invoice.payment_url = res["checkout_url"]
    db.commit()
    return StripeCheckoutResponse(
        checkout_url=res["checkout_url"],
        session_id=res["session_id"],
    )


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = invoice_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
def mark_paid(
    invoice_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = "paid"
    invoice.paid_date = date.today()

    # Cancel pending reminders (Remediation: actively set status to cancelled)
    for reminder in invoice.reminders:
        if reminder.sent_at is None:
            reminder.status = "cancelled"

    audit = AuditLog(
        user_id=current_user.id,
        action="INVOICE_PAID",
        ip_address=request.client.host if request.client else None,
        details=f"Invoice {invoice.invoice_number} marked as paid",
    )
    db.add(audit)
    db.commit()

    dispatch_event("invoice.paid", {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "amount": float(invoice.amount),
        "currency": invoice.currency,
        "paid_date": str(invoice.paid_date),
    })

    db.refresh(invoice)
    return invoice

