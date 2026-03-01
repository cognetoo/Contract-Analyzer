from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from api.db import get_db
from api.models import User
from api.security import hash_password, verify_password, create_access_token
from api.deps import get_current_user

from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

import re


# ------------------ Schemas ------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str


# ------------------ Register ------------------

import re

def validate_password(pw: str):
    if len(pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", pw):
        raise HTTPException(status_code=400, detail="Password must include an uppercase letter.")
    if not re.search(r"[a-z]", pw):
        raise HTTPException(status_code=400, detail="Password must include a lowercase letter.")
    if not re.search(r"\d", pw):
        raise HTTPException(status_code=400, detail="Password must include a number.")
    if not re.search(r"[^A-Za-z0-9]", pw):
        raise HTTPException(status_code=400, detail="Password must include a special character.")

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        select(User).where(User.email == req.email)
    ).scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    validate_password(req.password)
    
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return AuthResponse(access_token=token)


# ------------------ Login (OAuth2 form style) ------------------

@router.post("/login", response_model=AuthResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.execute(
        select(User).where(User.email == form.username)
    ).scalars().first()

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return AuthResponse(access_token=token)


# ------------------ /me route (IMPORTANT) ------------------

@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}