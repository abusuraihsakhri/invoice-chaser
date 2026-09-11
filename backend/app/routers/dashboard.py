from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Invoice, Reminder
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Total outstanding (sent + overdue invoices)
    outstanding = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status.in_(["sent", "overdue"]),
        )
        .scalar()
    )

    # Total overdue
    today = date.today()
    overdue_total = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == "overdue",
        )
        .scalar()
    )

    # Overdue count
    overdue_count = (
        db.query(func.count(Invoice.id))
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == "overdue",
        )
        .scalar()
    )

    # Invoices sent
    invoices_sent = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.user_id == current_user.id)
        .scalar()
    )

    # Invoices paid
    invoices_paid = (
        db.query(func.count(Invoice.id))
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == "paid",
        )
        .scalar()
    )

    # Reminders sent
    reminders_sent = (
        db.query(func.count(Reminder.id))
        .join(Invoice)
        .filter(
            Invoice.user_id == current_user.id,
            Reminder.sent_at.isnot(None),
        )
        .scalar()
    )

    # Average days to payment (Database-agnostic Python calculation)
    paid_invoices = (
        db.query(Invoice.issued_date, Invoice.paid_date)
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status == "paid",
            Invoice.paid_date.isnot(None),
        )
        .all()
    )
    if paid_invoices:
        day_diffs = [(inv.paid_date - inv.issued_date).days for inv in paid_invoices if inv.paid_date and inv.issued_date]
        avg_days = sum(day_diffs) / len(day_diffs) if day_diffs else None
    else:
        avg_days = None

    return DashboardStats(
        total_outstanding=outstanding,
        total_overdue=overdue_total,
        overdue_count=overdue_count,
        invoices_sent=invoices_sent,
        invoices_paid=invoices_paid,
        reminders_sent=reminders_sent,
        avg_days_to_payment=round(avg_days, 1) if avg_days is not None else None,
    )

