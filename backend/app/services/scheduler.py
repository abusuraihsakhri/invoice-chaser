import logging
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import Invoice, Reminder
from app.services.email_sender import send_reminder_email
from app.services.integrations.webhook_service import dispatch_event
from app.services.intelligent_engine import calculate_invoice_risk

logger = logging.getLogger("invoice_chaser.scheduler")
scheduler = BackgroundScheduler()


def check_and_send_reminders():
    """Check for due reminders and send them."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find reminders that are due and pending
        due_reminders = (
            db.query(Reminder)
            .join(Invoice)
            .filter(
                Reminder.scheduled_at <= now,
                Reminder.sent_at.is_(None),
                Reminder.status == "pending",
                Invoice.status.in_(["sent", "overdue"]),
            )
            .all()
        )

        for reminder in due_reminders:
            send_reminder_email(reminder)

        db.commit()
        if due_reminders:
            logger.info("[SCHEDULER] Dispatched %d due reminders", len(due_reminders))

    except Exception as exc:
        logger.error("[SCHEDULER] Reminder dispatch error: %s", exc)
    finally:
        db.close()


def update_overdue_invoices():
    """Mark invoices as overdue if past due date, update risk score, and alert webhooks."""
    db = SessionLocal()
    try:
        today = date.today()

        overdue_invoices = (
            db.query(Invoice)
            .filter(
                Invoice.due_date < today,
                Invoice.status == "sent",
            )
            .all()
        )

        for invoice in overdue_invoices:
            invoice.status = "overdue"
            # Recalculate risk score
            if invoice.client:
                risk = calculate_invoice_risk(invoice, invoice.client)
                invoice.risk_score = risk["risk_score"]
                invoice.client.risk_score = risk["risk_score"]
                invoice.client.risk_tier = risk["risk_tier"]

            # Alert Webhooks
            dispatch_event("invoice.overdue", {
                "invoice_number": invoice.invoice_number,
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "client_name": invoice.client.name if invoice.client else "Unknown",
                "days_overdue": (today - invoice.due_date).days,
            })

        db.commit()
        if overdue_invoices:
            logger.info("[SCHEDULER] Marked %d invoices as overdue", len(overdue_invoices))

    except Exception as exc:
        logger.error("[SCHEDULER] Overdue status check error: %s", exc)
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        scheduler.add_job(check_and_send_reminders, "interval", minutes=5, id="check_reminders", replace_existing=True)
        scheduler.add_job(update_overdue_invoices, "cron", hour=0, minute=0, id="update_overdue", replace_existing=True)
        scheduler.start()
        logger.info("[SCHEDULER] Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[SCHEDULER] Background scheduler stopped")

