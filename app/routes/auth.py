import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from ..deps import current_user
from ..security import DUMMY_HASH, create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
_EMAIL = re.compile(r"^\S+@\S+\.\S+$")


class RegisterIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=100)
    username: Optional[str] = Field(default=None, max_length=100)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: Optional[str] = Field(default=None, max_length=254)
    username: Optional[str] = Field(default=None, max_length=254)
    password: str = Field(max_length=128)


def _session(user: dict) -> dict:
    token = create_token(user["id"], settings.secret_key, settings.token_days)
    return {
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
        },
    }


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    name = (body.name or body.full_name or body.username or "").strip()
    email = body.email.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Enter your name.")
    if not _EMAIL.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    user = db.create_user(name, email, hash_password(body.password))
    if user is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return _session(user)


@router.post("/login")
def login(body: LoginIn):
    email_or_user = (body.email or body.username or "").strip().lower()
    if not email_or_user:
        raise HTTPException(status_code=422, detail="Enter your email.")
    user = db.get_user_by_email(email_or_user)
    if user is None:
        verify_password(body.password, DUMMY_HASH)  # same work as a real check
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _session(user)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }
