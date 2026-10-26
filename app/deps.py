from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import db
from .config import settings
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> dict:
    """Reads 'Authorization: Bearer <token>'. The frontend logs the user out on any 401."""
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user_id = decode_token(creds.credentials, settings.secret_key)
    user = db.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user
