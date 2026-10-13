import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, timedelta

from app.main import app
from app.database import Base, get_db
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite database with StaticPool so all connections share the same memory DB
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)



def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_and_registration():
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "email": "test@enterprise.com",
        "password": "SuperSecretPassword123!",
        "business_name": "Acme Corp",
        "tone_preference": "professional",
        "currency": "USD",
    })
    assert reg_res.status_code == 200
    token_data = reg_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "email": "test@enterprise.com",
        "password": "SuperSecretPassword123!",
    })
    assert login_res.status_code == 200

    # 3. Get Me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test@enterprise.com"


def test_clients_and_invoices_workflow():
    # Register user
    reg_res = client.post("/api/auth/register", json={
        "email": "billing@agency.com",
        "password": "SecurePassword123!",
        "business_name": "Creative Agency",
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Client
    c_res = client.post("/api/clients", headers=headers, json={
        "name": "Global Tech Ltd",
        "email": "ap@globaltech.com",
        "company": "Global Tech",
        "notes": "Always requests net-30 terms",
    })
    assert c_res.status_code == 200
    client_id = c_res.json()["id"]

    # Export Clients CSV
    csv_client_res = client.get("/api/clients/export/csv", headers=headers)
    assert csv_client_res.status_code == 200
    assert "Global Tech" in csv_client_res.text

    # Create Invoice
    due = (date.today() + timedelta(days=14)).isoformat()
    inv_res = client.post("/api/invoices", headers=headers, json={
        "client_id": client_id,
        "amount": 2500.00,
        "description": "Full-stack web and mobile application development",
        "issued_date": date.today().isoformat(),
        "due_date": due,
    })
    assert inv_res.status_code == 200
    inv = inv_res.json()
    invoice_id = inv["id"]
    assert inv["amount"] == "2500.00"
    assert inv["status"] == "sent"

    # Verify Reminders were auto-scheduled
    rem_res = client.get(f"/api/reminders?invoice_id={invoice_id}", headers=headers)
    assert rem_res.status_code == 200
    reminders = rem_res.json()
    assert len(reminders) >= 3

    # Generate & Download PDF
    pdf_res = client.get(f"/api/invoices/{invoice_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 500  # Non-empty PDF binary

    # Test Intelligence: Risk Assessment
    risk_res = client.get(f"/api/intelligence/invoices/{invoice_id}/risk", headers=headers)
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "risk_score" in risk_data
    assert "default_probability_pct" in risk_data

    # Test Intelligence: Dynamic Tone Escalation
    tone_res = client.post("/api/intelligence/escalate-tone", headers=headers, json={
        "invoice_id": invoice_id,
        "target_tone": "firm",
    })
    assert tone_res.status_code == 200
    assert "subject" in tone_res.json()
    assert "body" in tone_res.json()

    # Test Intelligence: Payment Plan
    plan_res = client.post(f"/api/intelligence/invoices/{invoice_id}/payment-plan", headers=headers, json={
        "installments_count": 2,
        "frequency_days": 14,
        "notes": "Agreed 50% split",
    })
    assert plan_res.status_code == 200
    assert plan_res.json()["installments_count"] == 2

    # Test Mark Paid (Cancels pending reminders)
    paid_res = client.post(f"/api/invoices/{invoice_id}/mark-paid", headers=headers)
    assert paid_res.status_code == 200
    assert paid_res.json()["status"] == "paid"

    # Verify Reminders are cancelled
    updated_rems = client.get(f"/api/reminders?invoice_id={invoice_id}", headers=headers).json()
    for r in updated_rems:
        if not r["sent_at"]:
            assert r["status"] == "cancelled"

    # Export Invoices CSV
    inv_csv_res = client.get("/api/invoices/export/csv", headers=headers)
    assert inv_csv_res.status_code == 200
    assert "2500.00" in inv_csv_res.text


def test_tenant_isolation_and_invoice_number_uniqueness():
    """Two owners can create invoices without sharing clients or invoice numbers."""
    tokens = []
    clients = []
    for i in (1, 2):
        reg = client.post("/api/auth/register", json={
            "email": f"owner-{i}@example.com",
            "password": "SecurePassword123!",
        })
        assert reg.status_code == 200
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        tokens.append(headers)
        res = client.post("/api/clients", headers=headers, json={
            "name": f"Client {i}", "email": f"client-{i}@example.com"
        })
        assert res.status_code == 200
        clients.append(res.json()["id"])

    today = date.today()
    payload = {
        "amount": "10.00",
        "issued_date": today.isoformat(),
        "due_date": (today + timedelta(days=5)).isoformat(),
    }
    a = client.post("/api/invoices", headers=tokens[0], json={**payload, "client_id": clients[0]})
    b = client.post("/api/invoices", headers=tokens[1], json={**payload, "client_id": clients[1]})
    assert a.status_code == b.status_code == 200
    assert a.json()["invoice_number"] != b.json()["invoice_number"]

    invoice_id = a.json()["id"]
    denied = client.put(f"/api/invoices/{invoice_id}", headers=tokens[0], json={
        "client_id": clients[1]
    })
    assert denied.status_code == 404
    assert client.get(f"/api/invoices/{invoice_id}", headers=tokens[0]).json()["client_id"] == clients[0]
    assert client.get(f"/api/invoices/{invoice_id}", headers=tokens[1]).status_code == 404

    invalid = client.post("/api/invoices", headers=tokens[0], json={
        **payload, "client_id": clients[0],
        "due_date": (today - timedelta(days=1)).isoformat(),
    })
    assert invalid.status_code == 422
    invalid_cents = client.post("/api/invoices", headers=tokens[0], json={
        **payload, "client_id": clients[0], "amount": "2.345"
    })
    assert invalid_cents.status_code == 422

    # No fabricated payment link can be issued when Stripe is not configured.
    from app.config import settings
    if not settings.stripe_secret_key:
        link = client.post(f"/api/invoices/{invoice_id}/payment-link", headers=tokens[0])
        assert link.status_code == 503


def test_reminder_status_guards_and_bad_token():
    from app.auth import create_access_token
    malformed = create_access_token({"sub": "not-an-integer"})
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {malformed}"}).status_code == 401

    reg = client.post("/api/auth/register", json={
        "email": "guard@example.com", "password": "SecurePassword123!"
    })
    assert reg.status_code == 200
    auth = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    customer = client.post("/api/clients", headers=auth, json={
        "name": "Guarded Customer", "email": "guard-client@example.com"
    }).json()
    invoice = client.post("/api/invoices", headers=auth, json={
        "client_id": customer["id"], "amount": "20.00",
        "issued_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=7)).isoformat()
    }).json()
    reminders = client.get(f"/api/reminders?invoice_id={invoice['id']}", headers=auth).json()
    assert reminders
    rid = reminders[0]["id"]
    assert client.delete(f"/api/reminders/{rid}", headers=auth).status_code == 204
    assert client.post(f"/api/reminders/{rid}/send", headers=auth).status_code == 409

    paid = client.post(f"/api/invoices/{invoice['id']}/mark-paid", headers=auth)
    assert paid.status_code == 200
    assert client.post(f"/api/reminders/{reminders[-1]['id']}/send", headers=auth).status_code == 409


def test_unpaid_or_wrong_amount_stripe_event_cannot_settle_invoice(monkeypatch):
    from app.routers import integrations
    reg = client.post("/api/auth/register", json={
        "email": "webhook-test@example.com", "password": "SecurePassword123!"
    })
    assert reg.status_code == 200
    auth = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    customer = client.post("/api/clients", headers=auth, json={
        "name": "Payment Customer", "email": "payment-client@example.com"
    }).json()
    invoice = client.post("/api/invoices", headers=auth, json={
        "client_id": customer["id"], "amount": "30.50",
        "issued_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=7)).isoformat()
    }).json()

    session = {
        "client_reference_id": str(invoice["id"]),
        "payment_status": "unpaid",
        "amount_total": 3050,
        "currency": "usd",
    }
    event = {"type": "checkout.session.completed", "data": {"object": session}}
    monkeypatch.setattr(integrations, "verify_stripe_webhook", lambda body, sig: event)

    endpoint = "/api/integrations/webhooks/stripe"
    assert client.post(endpoint, content=b"test").json()["status"] == "ignored"
    session["payment_status"] = "paid"
    session["amount_total"] = 100
    assert client.post(endpoint, content=b"test").json()["status"] == "ignored"
    assert client.get(f"/api/invoices/{invoice['id']}", headers=auth).json()["status"] == "sent"

    session["amount_total"] = 3050
    assert client.post(endpoint, content=b"test").json()["status"] == "handled"
    assert client.get(f"/api/invoices/{invoice['id']}", headers=auth).json()["status"] == "paid"


def test_email_html_and_spreadsheet_formula_escaping():
    from types import SimpleNamespace
    from app.services.integrations.email_service import generate_html_email
    from app.services.integrations.export_service import export_clients_to_csv

    markup = generate_html_email(
        business_name="<script>alert(1)</script>",
        client_name="Client",
        invoice_number="INV<2",
        amount=12,
        currency="USD",
        due_date_str="Tomorrow",
        body_text="<img src=x onerror=alert(1)>",
        payment_url="javascript:alert(1)",
    )
    assert "<script>" not in markup
    assert "<img src=x" not in markup
    assert 'href="javascript:' not in markup
    assert "&lt;script&gt;" in markup
    row = SimpleNamespace(id=1, name="=1+1", email="safe@example.com",
                          company=None, phone=None, risk_score=15.0,
                          risk_tier="low", notes="+SUM(1,2)")
    exported = export_clients_to_csv([row])
    assert "'=1+1" in exported
    assert "'+SUM(1,2)" in exported


def test_unconfigured_email_is_not_reported_delivered(monkeypatch):
    from types import SimpleNamespace
    from app.config import settings
    from app.services.integrations.email_service import dispatch_reminder_email

    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_provider", "resend")
    invoice = SimpleNamespace(
        client=SimpleNamespace(name="Customer", email="someone@example.com"),
        user=SimpleNamespace(business_name="Our Co"),
        invoice_number="INV-1-999",
        amount=10,
        currency="USD",
        due_date=date.today(),
        payment_url=None,
    )
    reminder = SimpleNamespace(invoice=invoice, email_subject="Reminder", email_body="Pay invoice")
    success, reason = dispatch_reminder_email(reminder)
    assert success is False
    assert "provider" in reason.lower()


def test_payment_link_requires_https_and_production_requires_secret():
    from pydantic import ValidationError
    from app.config import Settings
    from app.schemas import InvoiceCreate, InvoiceUpdate

    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="")
    with pytest.raises(ValidationError):
        InvoiceCreate(
            client_id=1, amount="10.00", issued_date=date.today(),
            due_date=date.today(), payment_url="javascript:alert(1)"
        )
    with pytest.raises(ValidationError):
        InvoiceUpdate(payment_url="http://example.com/pay")
