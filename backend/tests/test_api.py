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
