"""Storage layer (SQLite via the standard library).

Every function opens a short-lived connection, so it is safe with FastAPI's threadpool.
When you move to PostgreSQL (Neon/Supabase), re-implement ONLY this file and keep the
function names - nothing else in the project touches the database.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_description TEXT NOT NULL,
    result_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, id DESC);
CREATE TABLE IF NOT EXISTS progress (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id   INTEGER NOT NULL,
    status     TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, skill_id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _tx():
    conn = _connect()
    try:
        with conn:  # commit on success, rollback on error
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _tx() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)


def _one(row) -> Optional[dict]:
    return dict(row) if row else None


# ---------- users ----------
def create_user(name: str, email: str, password_hash: str) -> Optional[dict]:
    """Returns the new user, or None if the email is already registered."""
    try:
        with _tx() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email, password_hash, _now()),
            )
            return _one(conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone())
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    with _tx() as conn:
        return _one(conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())


def get_user(user_id: int) -> Optional[dict]:
    with _tx() as conn:
        return _one(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


# ---------- analyses ----------
def save_analysis(user_id: int, job_description: str, result_json: str) -> int:
    with _tx() as conn:
        cur = conn.execute(
            "INSERT INTO analyses (user_id, job_description, result_json, created_at) VALUES (?, ?, ?, ?)",
            (user_id, job_description, result_json, _now()),
        )
        return cur.lastrowid


def latest_analysis(user_id: int) -> Optional[dict]:
    with _tx() as conn:
        return _one(conn.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone())


# ---------- roadmap progress ----------
def set_progress(user_id: int, skill_id: int, status: str) -> None:
    with _tx() as conn:
        conn.execute(
            "INSERT INTO progress (user_id, skill_id, status, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, skill_id) DO UPDATE SET status = excluded.status, "
            "updated_at = excluded.updated_at",
            (user_id, skill_id, status, _now()),
        )


def get_progress(user_id: int) -> dict:
    with _tx() as conn:
        rows = conn.execute("SELECT skill_id, status FROM progress WHERE user_id = ?", (user_id,)).fetchall()
    return {r["skill_id"]: r["status"] for r in rows}
