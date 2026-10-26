import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    """Tiny .env reader (KEY=value per line). Real environment variables win."""
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    # PowerShell's `echo X > .env` writes UTF-16; Notepad may add a BOM. Accept both.
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeError:
            continue
    else:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:  # a blank `SECRET_KEY=` must not override the default
            os.environ.setdefault(key.strip(), value)


_load_env()

_DEV_SECRET = "dev-only-secret-change-me-before-deploying-0123456789"


class Settings:
    secret_key = os.environ.get("SECRET_KEY") or _DEV_SECRET
    token_days = int(os.environ.get("TOKEN_DAYS", "7"))
    db_path = os.environ.get("DATABASE_PATH", str(BASE_DIR / "careerly.db"))
    cors_origins = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,null"
        ).split(",")
        if o.strip()
    ]


settings = Settings()

if settings.secret_key == _DEV_SECRET:
    print("WARNING: using the built-in dev SECRET_KEY. Set SECRET_KEY in .env before deploying.")
