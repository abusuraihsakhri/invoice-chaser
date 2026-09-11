import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import httpx

from app.config import settings

logger = logging.getLogger("invoice_chaser.email")


def generate_html_email(
    business_name: str,
    client_name: str,
    invoice_number: str,
    amount: float,
    currency: str,
    due_date_str: str,
    body_text: str,
    payment_url: Optional[str] = None,
) -> str:
    """Generate a clean, modern HTML email template for reminders."""
    currency_symbol = "$" if currency.upper() == "USD" else ("€" if currency.upper() == "EUR" else ("£" if currency.upper() == "GBP" else f"{currency} "))
    
    pay_button_html = ""
    if payment_url:
        pay_button_html = f"""
        <div style="margin: 28px 0; text-align: center;">
            <a href="{payment_url}" style="background-color: #4f46e5; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                Pay Invoice Now ({currency_symbol}{amount:,.2f}) &rarr;
            </a>
        </div>
        """

    paragraphs = "".join([f"<p style='margin: 0 0 16px 0; color: #374151; line-height: 1.6;'>{p.strip()}</p>" for p in body_text.split("\n\n") if p.strip()])

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Reminder</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6;">
    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <div style="background-color: #4f46e5; padding: 24px 32px; color: #ffffff;">
            <h1 style="margin: 0; font-size: 20px; font-weight: 700;">{business_name}</h1>
            <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 14px;">Invoice Notice &bull; {invoice_number}</p>
        </div>
        
        <div style="padding: 32px;">
            <div style="background-color: #f9fafb; border-left: 4px solid #4f46e5; padding: 16px; border-radius: 0 6px 6px 0; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #6b7280; font-size: 14px;">Invoice Number:</span>
                    <strong style="color: #111827; font-size: 14px;">{invoice_number}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #6b7280; font-size: 14px;">Amount Due:</span>
                    <strong style="color: #111827; font-size: 18px;">{currency_symbol}{amount:,.2f}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #6b7280; font-size: 14px;">Due Date:</span>
                    <strong style="color: #dc2626; font-size: 14px;">{due_date_str}</strong>
                </div>
            </div>

            <div style="font-size: 15px;">
                {paragraphs}
            </div>

            {pay_button_html}

            <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 32px 0 20px 0;">
            
            <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center;">
                Sent via {business_name} using Invoice Chaser &bull; Please reply directly to this email if you have questions.
            </p>
        </div>
    </div>
</body>
</html>
"""


def send_email_resend(to_email: str, subject: str, body_text: str, html_content: Optional[str] = None) -> bool:
    """Send transactional email via Resend API."""
    if not settings.resend_api_key:
        return False

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "text": body_text,
    }
    if html_content:
        payload["html"] = html_content

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            logger.info("Resend email sent to %s successfully: ID %s", to_email, resp.json().get("id"))
            return True
    except Exception as exc:
        logger.error("Resend delivery failed for %s: %s", to_email, exc)
        return False


def send_email_smtp(to_email: str, subject: str, body_text: str, html_content: Optional[str] = None) -> bool:
    """Send email via SMTP (standard mail servers, AWS SES, Gmail, etc.)."""
    if not settings.smtp_host or not settings.smtp_user:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from or settings.smtp_user
        msg["To"] = to_email

        # Attach text and html parts
        part1 = MIMEText(body_text, "plain", "utf-8")
        msg.attach(part1)
        if html_content:
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part2)

        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        
        server.sendmail(msg["From"], [to_email], msg.as_string())
        server.quit()
        logger.info("SMTP email sent to %s successfully", to_email)
        return True
    except Exception as exc:
        logger.error("SMTP delivery failed for %s: %s", to_email, exc)
        return False


def dispatch_reminder_email(reminder) -> tuple[bool, Optional[str]]:
    """Smart dispatcher: tries Resend -> SMTP -> Dev fallback."""
    to_email = reminder.invoice.client.email
    subject = reminder.email_subject or f"Reminder: Invoice {reminder.invoice.invoice_number}"
    body = reminder.email_body or ""
    
    html = generate_html_email(
        business_name=reminder.invoice.user.business_name or "Our Company",
        client_name=reminder.invoice.client.name,
        invoice_number=reminder.invoice.invoice_number,
        amount=float(reminder.invoice.amount),
        currency=reminder.invoice.currency or "USD",
        due_date_str=reminder.invoice.due_date.strftime("%B %d, %Y"),
        body_text=body,
        payment_url=reminder.invoice.payment_url,
    )

    # 1. Try Resend if configured
    if settings.resend_api_key:
        success = send_email_resend(to_email, subject, body, html)
        if success:
            return True, None
        logger.warning("Resend failed; attempting SMTP fallback if configured")

    # 2. Try SMTP if configured
    if settings.smtp_host and settings.smtp_user:
        success = send_email_smtp(to_email, subject, body, html)
        if success:
            return True, None

    # 3. Fallback: Log to console in development mode
    logger.info("[DEV / DEMO EMAIL] Sent to %s | Subject: %s", to_email, subject)
    return True, "Simulated delivery (no active mail API key configured)"
