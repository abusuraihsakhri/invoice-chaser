from datetime import datetime, date
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from decimal import Decimal


# --- User Schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    business_name: Optional[str] = None
    tone_preference: Optional[str] = "professional"
    currency: Optional[str] = "USD"
    invoice_prefix: Optional[str] = "INV"
    phone: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    business_name: Optional[str] = None
    tone_preference: str
    currency: str = "USD"
    invoice_prefix: str = "INV"
    phone: Optional[str] = None
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


# --- Client Schemas ---

class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    risk_score: float = 15.0
    risk_tier: str = "low"
    created_at: datetime


# --- Invoice Schemas ---

class InvoiceCreate(BaseModel):
    client_id: int
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = "USD"
    description: Optional[str] = None
    payment_url: Optional[str] = None
    issued_date: date
    due_date: date


class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    payment_url: Optional[str] = None
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[str] = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    client_id: int
    invoice_number: str
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    status: str
    payment_url: Optional[str] = None
    risk_score: float = 15.0
    issued_date: date
    due_date: date
    paid_date: Optional[date] = None
    created_at: datetime
    client: Optional[ClientResponse] = None


# --- Reminder Schemas ---

class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    reminder_type: Optional[str] = None
    tone: Optional[str] = None
    status: str = "pending"
    delivery_channel: str = "email"
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    opened: bool = False
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    invoice: Optional[InvoiceResponse] = None


class ReminderEdit(BaseModel):
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    scheduled_at: Optional[datetime] = None


# --- Payment Plan Schemas ---

class PaymentPlanCreate(BaseModel):
    installments_count: int = Field(2, ge=2, le=12)
    frequency_days: int = Field(14, ge=1, le=90)
    notes: Optional[str] = None


class PaymentPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    total_amount: Decimal
    installments_count: int
    installment_amount: Decimal
    frequency_days: int
    status: str
    notes: Optional[str] = None
    created_at: datetime


# --- Intelligence & Negotiation Schemas ---

class RiskAssessmentResponse(BaseModel):
    invoice_id: int
    risk_score: float
    risk_tier: str  # low, medium, high, severe
    default_probability_pct: float
    expected_delay_days: int
    key_factors: List[str]
    recommended_action: str
    discount_incentive_suggested: Optional[str] = None


class ToneEscalationRequest(BaseModel):
    invoice_id: int
    target_tone: str  # friendly, professional, firm, urgent, final, legal
    custom_instruction: Optional[str] = None


class ToneEscalationResponse(BaseModel):
    tone: str
    subject: str
    body: str
    recommended_send_hour_utc: int = 14  # 9 AM EST
    projected_response_rate_pct: float


class DisputeDraftRequest(BaseModel):
    invoice_id: int
    client_excuse: str  # e.g., "waiting on our client to pay us", "cash flow crunch", "disputing charges"


class DisputeDraftResponse(BaseModel):
    scenario: str
    recommended_reply_subject: str
    recommended_reply_body: str
    settlement_offer: Optional[str] = None


# --- Integrations Schemas ---

class IntegrationConfigUpdate(BaseModel):
    service_name: str  # stripe, resend, smtp, slack, discord
    is_active: bool = True
    config_data: Dict[str, Any]


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StripeCheckoutRequest(BaseModel):
    invoice_id: int
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class StripeCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class WebhookTestRequest(BaseModel):
    service: str  # slack, discord, generic
    webhook_url: str


# --- Dashboard Schemas ---

class DashboardStats(BaseModel):
    total_outstanding: Decimal
    total_overdue: Decimal
    overdue_count: int
    invoices_sent: int
    invoices_paid: int
    reminders_sent: int
    avg_days_to_payment: Optional[float] = None

