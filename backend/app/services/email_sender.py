import logging
from datetime import datetime
from app.services.integrations.email_service import dispatch_reminder_email
from app.services.integrations.webhook_service import dispatch_event

logger = logging.getLogger("invoice_chaser.sender")


def send_reminder_email(reminder) -> bool:
    """Send a reminder email via configured integration (Resend / SMTP / Local)."""
    try:
        success, message = dispatch_reminder_email(reminder)
        if success:
            reminder.sent_at = datetime.utcnow()
            reminder.status = "sent"
            reminder.error_message = message

            # Outgoing Webhook Event
            dispatch_event("reminder.sent", {
                "reminder_id": reminder.id,
                "invoice_number": reminder.invoice.invoice_number,
                "client_email": reminder.invoice.client.email,
                "tone": reminder.tone,
                "subject": reminder.email_subject,
            })
            return True
        else:
            reminder.status = "failed"
            reminder.error_message = "All delivery providers failed"
            return False
    except Exception as exc:
        logger.error("Exception during reminder dispatch: %s", exc)
        reminder.status = "failed"
        reminder.error_message = str(exc)
        return False

