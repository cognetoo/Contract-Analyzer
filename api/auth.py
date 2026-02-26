from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.db import get_db
from api.models import User
from api.security import hash_password, verify_password, create_access_token

from pydantic import BaseModel, EmailStr, field_validator

from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])


def _password_bytes_len(pw: str) -> int:
    return len((pw or "").encode("utf-8"))


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        # bcrypt hard limit
        if _password_bytes_len(v) > 72:
            raise ValueError("Password must be <= 72 bytes (bcrypt limit).")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        # keep same 72-byte rule to avoid bcrypt errors on verify
        if not v:
            raise ValueError("Password is required.")
        if _password_bytes_len(v) > 72:
            raise ValueError("Password must be <= 72 bytes (bcrypt limit).")
        return v


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == req.email)).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    u = User(
        email=req.email,
        password_hash=hash_password(req.password),
        is_active=True,
    )
    db.add(u)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # handles race condition + unique constraint
        raise HTTPException(status_code=409, detail="Email already registered")

    db.refresh(u)

    token = create_access_token({"sub": str(u.id)})
    return AuthResponse(access_token=token)


@router.post("/login", response_model=AuthResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # form.username will contain the email
    u = db.execute(select(User).where(User.email == form.username)).scalars().first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(u.id)})
    return AuthResponse(access_token=token)