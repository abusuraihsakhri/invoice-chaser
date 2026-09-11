from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, AuditLog
from app.schemas import UserCreate, UserResponse, UserLogin, Token
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Check if user exists (case-insensitive email lookup)
    normalized_email = user_data.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password complexity
    if len(user_data.password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 non-empty characters long",
        )

    # Create user
    user = User(
        email=normalized_email,
        password_hash=get_password_hash(user_data.password),
        business_name=user_data.business_name,
        tone_preference=user_data.tone_preference or "professional",
        currency=user_data.currency or "USD",
        invoice_prefix=user_data.invoice_prefix or "INV",
        phone=user_data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="AUTH_REGISTER",
        ip_address=request.client.host if request.client else None,
        details=f"User registered with email {user.email}",
    )
    db.add(audit)
    db.commit()

    # Generate token
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    normalized_email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="AUTH_LOGIN",
        ip_address=request.client.host if request.client else None,
        details=f"User logged in: {user.email}",
    )
    db.add(audit)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

