from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Reminder, Invoice
from app.schemas import ReminderResponse, ReminderEdit
from app.services.email_sender import send_reminder_email

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=List[ReminderResponse])
def list_reminders(
    invoice_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.client))
        .join(Invoice)
        .filter(Invoice.user_id == current_user.id)
    )
    if invoice_id:
        query = query.filter(Reminder.invoice_id == invoice_id)
    return query.order_by(Reminder.scheduled_at.asc()).all()


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.client))
        .join(Invoice)
        .filter(
            Reminder.id == reminder_id,
            Invoice.user_id == current_user.id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.put("/{reminder_id}", response_model=ReminderResponse)
def edit_reminder(
    reminder_id: int,
    edit_data: ReminderEdit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.client))
        .join(Invoice)
        .filter(
            Reminder.id == reminder_id,
            Invoice.user_id == current_user.id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if edit_data.email_subject is not None:
        reminder.email_subject = edit_data.email_subject
    if edit_data.email_body is not None:
        reminder.email_body = edit_data.email_body
    if edit_data.scheduled_at is not None:
        reminder.scheduled_at = edit_data.scheduled_at

    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .join(Invoice)
        .filter(
            Reminder.id == reminder_id,
            Invoice.user_id == current_user.id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.status = "cancelled"
    db.commit()


@router.post("/{reminder_id}/send", response_model=ReminderResponse)
def send_reminder_now(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.client))
        .join(Invoice)
        .filter(
            Reminder.id == reminder_id,
            Invoice.user_id == current_user.id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.status == "sent":
        raise HTTPException(status_code=400, detail="Reminder has already been sent")

    # Dispatch email
    success = send_reminder_email(reminder)
    db.commit()
    db.refresh(reminder)

    if not success and reminder.status == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send email: {reminder.error_message}",
        )

    return reminder

