import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
import httpx

from app.config import settings

logger = logging.getLogger("invoice_chaser.webhook")


def dispatch_event(event_name: str, payload: Dict[str, Any]):
    """Dispatch an event asynchronously/synchronously to configured webhooks."""
    # 1. Slack Webhook
    if settings.slack_webhook_url:
        _send_slack(event_name, payload)

    # 2. Discord Webhook
    if settings.discord_webhook_url:
        _send_discord(event_name, payload)

    # 3. Generic Webhook
    if settings.generic_webhook_url:
        _send_generic(event_name, payload)


def _send_slack(event_name: str, payload: Dict[str, Any]):
    title = f":bell: *Invoice Chaser Alert:* `{event_name}`"
    text = f"{title}\n```\n{json.dumps(payload, indent=2, default=str)}\n```"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(settings.slack_webhook_url, json={"text": text})
    except Exception as exc:
        logger.warning("Failed to send Slack webhook: %s", exc)


def _send_discord(event_name: str, payload: Dict[str, Any]):
    content = f"**[Invoice Chaser]** Event: `{event_name}`\n```{json.dumps(payload, indent=2, default=str)[:1800]}```"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(settings.discord_webhook_url, json={"content": content})
    except Exception as exc:
        logger.warning("Failed to send Discord webhook: %s", exc)


def _send_generic(event_name: str, payload: Dict[str, Any]):
    body = json.dumps({"event": event_name, "data": payload}, default=str)
    headers = {"Content-Type": "application/json", "User-Agent": "InvoiceChaser-Webhook/1.0"}
    
    if settings.webhook_secret:
        signature = hmac.new(
            settings.webhook_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Signature-256"] = signature

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(settings.generic_webhook_url, content=body, headers=headers)
    except Exception as exc:
        logger.warning("Failed to dispatch generic webhook: %s", exc)
