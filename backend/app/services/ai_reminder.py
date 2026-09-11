from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Reminder, Invoice, User, Client
from app.services.intelligent_engine import (
    generate_ai_reminder_message,
    calculate_invoice_risk,
)

# Comprehensive Escalation Schedule
REMINDER_SCHEDULE = [
    {"days_offset": -1, "tone": "friendly", "type": "pre_due"},
    {"days_offset": 0, "tone": "professional", "type": "on_due"},
    {"days_offset": 7, "tone": "firm", "type": "post_due_7"},
    {"days_offset": 14, "tone": "urgent", "type": "post_due_14"},
    {"days_offset": 30, "tone": "final", "type": "post_due_30"},
]


def generate_reminder_content(db: Session, invoice: Invoice, user: User, client: Client):
    """Generate AI-powered reminder schedule with risk assessment."""
    # 1. Calculate & record risk score
    risk_data = calculate_invoice_risk(invoice, client)
    invoice.risk_score = risk_data["risk_score"]
    client.risk_score = risk_data["risk_score"]
    client.risk_tier = risk_data["risk_tier"]

    # 2. Schedule reminders
    for schedule in REMINDER_SCHEDULE:
        scheduled_time = datetime.combine(
            invoice.due_date + timedelta(days=schedule["days_offset"]),
            datetime.min.time(),  # midnight
        )

        # Skip past dates unless testing today's invoice
        if scheduled_time < datetime.utcnow() and schedule["days_offset"] < 0:
            continue

        subject, body = generate_ai_reminder_message(
            business_name=user.business_name or "Our Company",
            client_name=client.name,
            client_notes=client.notes,
            invoice_number=invoice.invoice_number,
            amount=float(invoice.amount),
            currency=invoice.currency or user.currency or "USD",
            description=invoice.description,
            due_date_str=invoice.due_date.strftime("%B %d, %Y"),
            days_offset=schedule["days_offset"],
            tone=schedule["tone"],
        )

        reminder = Reminder(
            invoice_id=invoice.id,
            reminder_type=schedule["type"],
            tone=schedule["tone"],
            status="pending",
            delivery_channel="email",
            scheduled_at=scheduled_time,
            email_subject=subject,
            email_body=body,
        )
        db.add(reminder)

    db.commit()

