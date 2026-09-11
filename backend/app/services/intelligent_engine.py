import json
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional, List
import httpx

from app.config import settings

logger = logging.getLogger("invoice_chaser.intelligence")


# --- Prompt Injection Defense Sanitizer ---
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|all)\s+instructions",
    r"(?i)system\s*prompt",
    r"(?i)you\s+are\s+now",
    r"(?i)disregard\s+above",
    r"(?i)admin\s+mode",
    r"(?i)reveal\s+secret",
]

def sanitize_user_input(text: Optional[str], max_len: int = 500) -> str:
    """Sanitize user-provided fields (notes, descriptions) to neutralize prompt injection."""
    if not text:
        return "None provided"
    cleaned = text[:max_len].strip()
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[sanitized]", cleaned)
    # Escape XML delimiters
    cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;")
    return cleaned


# --- Risk Assessment & Default Prediction Engine ---
def calculate_invoice_risk(invoice, client, user_invoices_history: List[Any] = None) -> Dict[str, Any]:
    """Calculate payment default risk score (0-100), tier, and recommendations."""
    score = 10.0  # Baseline low risk
    factors = []

    today = date.today()
    days_overdue = (today - invoice.due_date).days if today > invoice.due_date else 0
    amount = float(invoice.amount)

    # Factor 1: Overdue timeline
    if days_overdue > 30:
        score += 45.0
        factors.append(f"Severely overdue by {days_overdue} days")
    elif days_overdue > 14:
        score += 30.0
        factors.append(f"Overdue by {days_overdue} days (>2 weeks)")
    elif days_overdue > 7:
        score += 20.0
        factors.append(f"Overdue by {days_overdue} days")
    elif days_overdue > 0:
        score += 10.0
        factors.append(f"Past due date by {days_overdue} days")

    # Factor 2: Amount exposure
    if amount > 10000:
        score += 15.0
        factors.append("High capital exposure (> $10,000)")
    elif amount > 5000:
        score += 8.0
        factors.append("Moderate capital exposure (> $5,000)")

    # Factor 3: Client notes keyword heuristics
    notes_lower = (client.notes or "").lower()
    if any(k in notes_lower for k in ["late", "unresponsive", "ghost", "delay", "slow"]):
        score += 20.0
        factors.append("Client profile has historical slow-payment / friction notes")
    elif any(k in notes_lower for k in ["vip", "prompt", "reliable", "on-time", "good"]):
        score = max(5.0, score - 10.0)
        factors.append("Client has verified high-reliability reputation")

    score = min(98.0, max(5.0, score))

    if score < 25.0:
        tier = "low"
        action = "Standard automated reminders; high likelihood of timely settlement."
        discount = None
        expected_delay = 0 if days_overdue == 0 else min(5, days_overdue + 2)
    elif score < 50.0:
        tier = "medium"
        action = "Friendly check-in reminder; confirm receipt of invoice with accounts payable."
        discount = "Offer 2% prompt settlement incentive if cleared within 48 hours."
        expected_delay = max(7, days_overdue + 5)
    elif score < 75.0:
        tier = "high"
        action = "Escalate tone to firm; schedule a direct phone follow-up with client management."
        discount = "Offer 5% instant settlement or propose 2-installment payment plan."
        expected_delay = max(18, days_overdue + 12)
    else:
        tier = "severe"
        action = "Final demand notice required; issue formal pre-legal collections warning."
        discount = "Propose structured emergency payment plan to salvage debt."
        expected_delay = max(35, days_overdue + 25)

    return {
        "invoice_id": invoice.id,
        "risk_score": round(score, 1),
        "risk_tier": tier,
        "default_probability_pct": round(score * 0.92, 1),
        "expected_delay_days": expected_delay,
        "key_factors": factors or ["Normal invoice lifecycle within standard credit terms"],
        "recommended_action": action,
        "discount_incentive_suggested": discount,
    }


# --- Multi-Provider AI Caller ---
def generate_ai_reminder_message(
    business_name: str,
    client_name: str,
    client_notes: Optional[str],
    invoice_number: str,
    amount: float,
    currency: str,
    description: Optional[str],
    due_date_str: str,
    days_offset: int,
    tone: str,
    custom_instruction: Optional[str] = None,
) -> Tuple[str, str]:
    """Generate tone-tailored reminder copy using the configured AI provider with intelligent fallback."""
    curr_symbol = "$" if currency.upper() == "USD" else (f"{currency} ")
    sanitized_notes = sanitize_user_input(client_notes)
    sanitized_desc = sanitize_user_input(description)
    sanitized_instruction = sanitize_user_input(custom_instruction) if custom_instruction else ""

    # Check for API keys
    api_key = (
        settings.hermes_api_key
        or settings.openai_api_key
        or settings.gemini_api_key
        or settings.anthropic_api_key
    )

    if not api_key:
        return _offline_intelligent_template(
            business_name=business_name,
            client_name=client_name,
            invoice_number=invoice_number,
            amount=amount,
            curr_symbol=curr_symbol,
            due_date_str=due_date_str,
            days_offset=days_offset,
            tone=tone,
        )

    # Compose system & user prompts
    system_prompt = (
        "You are an elite, highly professional B2B credit controller and accounts receivable specialist. "
        "Your task is to write high-converting, professional payment reminder emails. "
        "You MUST respond ONLY with valid JSON containing exactly two keys: 'subject' and 'body'. "
        "Do not include markdown code block backticks around the JSON."
    )

    user_prompt = f"""Write an accounts receivable reminder email with the following parameters:
- Sender Business: {business_name}
- Client Name: {client_name}
- Invoice Number: {invoice_number}
- Amount: {curr_symbol}{amount:,.2f}
- Due Date: {due_date_str}
- Timing Status: {"Due tomorrow" if days_offset == -1 else "Due today" if days_offset == 0 else f"{days_offset} days overdue"}
- Requested Tone: {tone} (escalation level)
<client_context>{sanitized_notes}</client_context>
<invoice_description>{sanitized_desc}</invoice_description>
{"Special Instruction: " + sanitized_instruction if sanitized_instruction else ""}

Requirements:
1. Embody the {tone} tone precisely.
2. Clearly state invoice #{invoice_number} and amount {curr_symbol}{amount:,.2f}.
3. Provide a clear, polite call-to-action for immediate payment.
4. Output JSON: {{"subject": "...", "body": "..."}}"""

    try:
        # 1. Hermes / OpenAI-compatible endpoint
        endpoint = settings.hermes_api_url if settings.hermes_api_key else "https://api.openai.com/v1/chat/completions"
        model_name = "hermes-3-llama-3.1-8b" if settings.hermes_api_key else "gpt-4o-mini"
        auth_header = f"Bearer {settings.hermes_api_key or settings.openai_api_key}"

        with httpx.Client(timeout=25.0) as client:
            res = client.post(
                endpoint,
                headers={"Authorization": auth_header, "Content-Type": "application/json"},
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.5,
                },
            )
            res.raise_for_status()
            data = res.json()
            raw_content = data["choices"][0]["message"]["content"].strip()
            # Strip potential ```json wrapper
            if raw_content.startswith("```"):
                raw_content = re.sub(r"^```json\s*", "", raw_content)
                raw_content = re.sub(r"```$", "", raw_content).strip()
            parsed = json.loads(raw_content)
            return parsed["subject"], parsed["body"]
    except Exception as exc:
        logger.warning("AI provider call failed (%s). Using offline intelligent fallback.", exc)
        return _offline_intelligent_template(
            business_name=business_name,
            client_name=client_name,
            invoice_number=invoice_number,
            amount=amount,
            curr_symbol=curr_symbol,
            due_date_str=due_date_str,
            days_offset=days_offset,
            tone=tone,
        )


# --- Dispute & Excuse AI Responder ---
def generate_dispute_response(
    invoice,
    client,
    client_excuse: str,
) -> Dict[str, str]:
    """Generate professional negotiation replies for typical debtor stall tactics."""
    excuse_clean = client_excuse.lower()
    amount = float(invoice.amount)
    curr = invoice.currency or "USD"
    curr_sym = "$" if curr == "USD" else f"{curr} "

    if "not received" in excuse_clean or "didn't get" in excuse_clean or "lost" in excuse_clean:
        scenario = "Missing / Unreceived Invoice Claim"
        subject = f"Re: Invoice {invoice.invoice_number} Copy Attached - {curr_sym}{amount:,.2f}"
        body = (
            f"Hi {client.name},\n\n"
            f"Thank you for getting back to us. To ensure you have all the necessary records for processing, "
            f"we have re-attached a copy of Invoice {invoice.invoice_number} ({curr_sym}{amount:,.2f}), originally issued on {invoice.issued_date.strftime('%B %d, %Y')}.\n\n"
            f"Could you please confirm receipt and let us know your scheduled payment disbursement run date?\n\n"
            f"Best regards,\nAccounts Receivable Team"
        )
        offer = None
    elif "cash flow" in excuse_clean or "tight" in excuse_clean or "struggling" in excuse_clean or "cannot pay" in excuse_clean:
        scenario = "Cash Flow / Financial Hardship"
        subject = f"Flexible Payment Arrangement: Invoice {invoice.invoice_number}"
        half = amount / 2
        body = (
            f"Hi {client.name},\n\n"
            f"We understand cash flow fluctuations and value our working relationship with {client.company or client.name}. "
            f"To assist you while keeping accounts in good standing, we can offer a two-part installment plan:\n\n"
            f"1. First installment of {curr_sym}{half:,.2f} payable this week.\n"
            f"2. Remaining {curr_sym}{half:,.2f} payable in 14 days.\n\n"
            f"Please let us know if this structure works for you so we can update your account schedule.\n\n"
            f"Best regards,\nAccounts Receivable Team"
        )
        offer = f"Split balance into 2 installments of {curr_sym}{half:,.2f}"
    elif "dispute" in excuse_clean or "incorrect" in excuse_clean or "scope" in excuse_clean:
        scenario = "Billing or Scope Discrepancy"
        subject = f"Review Request: Invoice {invoice.invoice_number} Query"
        body = (
            f"Hi {client.name},\n\n"
            f"Thank you for raising your question regarding Invoice {invoice.invoice_number}. We want to resolve any confusion promptly.\n\n"
            f"Could you please detail the specific line item or deliverable you would like us to review? "
            f"We are happy to jump on a quick 10-minute call today to address this and align our records.\n\n"
            f"Best regards,\nAccounts Receivable Team"
        )
        offer = "Schedule immediate alignment review"
    else:
        scenario = "General Delay / Unspecified Hold"
        subject = f"Follow-up: Invoice {invoice.invoice_number} Payment Status"
        body = (
            f"Hi {client.name},\n\n"
            f"Thank you for following up regarding Invoice {invoice.invoice_number} for {curr_sym}{amount:,.2f}.\n\n"
            f"We would appreciate an update on when this has been scheduled for payment release so we can update our records.\n\n"
            f"Best regards,\nAccounts Receivable Team"
        )
        offer = None

    return {
        "scenario": scenario,
        "recommended_reply_subject": subject,
        "recommended_reply_body": body,
        "settlement_offer": offer,
    }


# --- Offline Heuristic Intelligent Fallback ---
def _offline_intelligent_template(
    business_name: str,
    client_name: str,
    invoice_number: str,
    amount: float,
    curr_symbol: str,
    due_date_str: str,
    days_offset: int,
    tone: str,
) -> Tuple[str, str]:
    """Rich rule-based escalation copy generator."""
    if tone == "friendly" or days_offset < 0:
        subject = f"Upcoming Invoice {invoice_number} Due Tomorrow ({curr_symbol}{amount:,.2f})"
        body = (
            f"Hi {client_name},\n\n"
            f"We hope you're having a productive week!\n\n"
            f"This is a quick courtesy note to remind you that Invoice {invoice_number} for "
            f"{curr_symbol}{amount:,.2f} is scheduled for payment tomorrow ({due_date_str}).\n\n"
            f"If payment is already scheduled or processing, please disregard this reminder. "
            f"Feel free to reply if you need any additional invoice copies or details.\n\n"
            f"Warm regards,\n{business_name}"
        )
    elif tone == "professional" or days_offset == 0:
        subject = f"Invoice {invoice_number} is Due Today - {business_name}"
        body = (
            f"Dear {client_name},\n\n"
            f"Please be advised that Invoice {invoice_number} for {curr_symbol}{amount:,.2f} is due for payment today ({due_date_str}).\n\n"
            f"Prompt settlement helps us keep your account in optimal standing and maintain uninterrupted service.\n\n"
            f"If payment has already been initiated, please let us know. Thank you for your partnership!\n\n"
            f"Sincerely,\n{business_name}"
        )
    elif tone == "firm" or days_offset <= 14:
        subject = f"Urgent: Payment Overdue for Invoice {invoice_number} ({days_offset} Days Overdue)"
        body = (
            f"Dear {client_name},\n\n"
            f"We have not yet received payment for Invoice {invoice_number} in the amount of {curr_symbol}{amount:,.2f}, "
            f"which reached maturity on {due_date_str} and is now {days_offset} days overdue.\n\n"
            f"Please arrange payment today or provide the transaction reference if payment has already been transmitted.\n\n"
            f"If there is any administrative or operational blocker preventing payment, please contact us immediately so we can assist.\n\n"
            f"Regards,\n{business_name}"
        )
    elif tone in ("urgent", "final") or days_offset <= 30:
        subject = f"FINAL NOTICE: Delinquent Balance for Invoice {invoice_number}"
        body = (
            f"Attention: {client_name},\n\n"
            f"This is a formal final notice regarding Invoice {invoice_number} for {curr_symbol}{amount:,.2f}, "
            f"which is now {days_offset} days past its due date ({due_date_str}).\n\n"
            f"Multiple reminders have been sent without resolution. We require settlement within 5 business days to prevent account suspension and escalation.\n\n"
            f"Please remit payment immediately to clear this balance.\n\n"
            f"Accounts Management,\n{business_name}"
        )
    else:  # Legal / Pre-collections
        subject = f"PRE-COLLECTIONS NOTICE: Formal Demand for Payment #{invoice_number}"
        body = (
            f"To the Management of {client_name},\n\n"
            f"Take notice that Invoice {invoice_number} for {curr_symbol}{amount:,.2f} remains severely unpaid ({days_offset} days past due).\n\n"
            f"Failure to remit full payment or contact our office within forty-eight (48) hours will result in referral of this matter to third-party collections and potential credit bureau reporting.\n\n"
            f"Govern yourself accordingly.\n\n"
            f"Credit & Collections Department,\n{business_name}"
        )

    return subject, body
