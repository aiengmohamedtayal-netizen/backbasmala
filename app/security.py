"""Password hashing (PBKDF2, standard library) and JWT tokens (PyJWT)."""
import hashlib
import hmac
import os
import time
from typing import Optional

import jwt

_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


# Used to spend the same time when the email does not exist (so timing does not reveal it).
DUMMY_HASH = hash_password("not-a-real-password")


def create_token(user_id: int, secret: str, days: int) -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + days * 86400},
                      secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> Optional[int]:
    try:
        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
