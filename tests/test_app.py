"""Tests for the layers that do not need FastAPI: security, database, response shape."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# use a throw-away database for tests
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")

import jwt
from app import db, views
from app.security import create_token, decode_token, hash_password, verify_password
from careerly_core import analyze_cv

db.init_db()
CV = "Python developer. Built REST APIs with Flask and MySQL. Git and GitHub daily. 2 years of Python."
JD = "Backend role. Python, FastAPI, PostgreSQL, Docker, Git required. Python and FastAPI daily. Nice to have: React."


def test_password_hashing():
    h = hash_password("correct horse")
    assert h.startswith("pbkdf2_sha256$") and "correct horse" not in h
    assert verify_password("correct horse", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", "garbage")
    assert hash_password("a" * 8) != hash_password("a" * 8)   # random salt

def test_tokens():
    t = create_token(7, "k" * 40, 1)
    assert decode_token(t, "k" * 40) == 7
    assert decode_token("Bearer " + t, "k" * 40) == 7         # gracefully handles Bearer prefix
    assert decode_token("  " + t + "  ", "k" * 40) == 7       # strips whitespace
    assert decode_token(t, "other" * 10) is None              # wrong secret
    assert decode_token("not.a.token", "k" * 40) is None
    expired = jwt.encode({"sub": "7", "exp": 1}, "k" * 40, algorithm="HS256")
    assert decode_token(expired, "k" * 40) is None
    none_alg = jwt.encode({"sub": "7"}, None, algorithm="none")
    assert decode_token(none_alg, "k" * 40) is None           # alg=none attack

def test_users():
    u = db.create_user("Sara", "sara@example.com", hash_password("password1"))
    assert u["id"] and u["email"] == "sara@example.com"
    assert db.create_user("Dup", "sara@example.com", "x") is None   # unique email
    assert db.get_user_by_email("sara@example.com")["id"] == u["id"]
    assert db.get_user(u["id"])["name"] == "Sara"
    assert db.get_user(9999) is None and db.get_user_by_email("no@x.com") is None

def test_analysis_and_progress_flow():
    u = db.create_user("Omar", "omar@example.com", hash_password("password1"))
    assert db.latest_analysis(u["id"]) is None
    payload = views.to_api(analyze_cv(CV, job_description=JD))
    db.save_analysis(u["id"], JD, json.dumps(payload))
    saved = json.loads(db.latest_analysis(u["id"])["result_json"])
    assert saved == payload

    # shape the frontend expects
    assert set(payload) == {"match_score", "target_role", "existing_skills", "missing_skills", "roadmap", "jobs"}
    assert isinstance(payload["match_score"], int)
    assert all(set(s) == {"id", "name", "category"} for s in payload["existing_skills"])
    assert all(set(s) == {"id", "name", "category", "priority"} for s in payload["missing_skills"])
    assert {m["name"] for m in payload["missing_skills"]} >= {"FastAPI", "PostgreSQL", "Docker"}
    assert all(m["priority"] in ("high", "medium", "low") for m in payload["missing_skills"])
    fast = next(m for m in payload["missing_skills"] if m["name"] == "FastAPI")
    assert fast["priority"] == "high"
    for item in payload["roadmap"]:
        assert set(item) == {"skill_id", "skill", "resources"}
        assert item["resources"] and all(set(r) == {"title", "type", "url"} for r in item["resources"])
        assert any(r["type"] == "youtube" and r["url"].startswith("https://www.youtube.com/results?search_query=")
                   for r in item["resources"])

    # progress is per user and merged into the roadmap
    first = payload["roadmap"][0]["skill_id"]
    assert all(r["status"] == "todo" for r in views.with_progress(payload, db.get_progress(u["id"]))["roadmap"])
    db.set_progress(u["id"], first, "in_progress")
    db.set_progress(u["id"], first, "done")                       # upsert, not duplicate
    merged = views.with_progress(payload, db.get_progress(u["id"]))
    assert merged["roadmap"][0]["status"] == "done"
    assert all(r["status"] == "todo" for r in merged["roadmap"][1:])
    other = db.create_user("Other", "other@example.com", hash_password("password1"))
    assert db.get_progress(other["id"]) == {}                      # not shared between users

    # a newer analysis becomes "latest"
    db.save_analysis(u["id"], "second", json.dumps({**payload, "match_score": 1}))
    assert json.loads(db.latest_analysis(u["id"])["result_json"])["match_score"] == 1


def test_api_auth_flow():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # 1. Register a new user
    reg = client.post("/auth/register", json={
        "name": "Kareem",
        "email": "kareem@example.com",
        "password": "strongPassword123"
    })
    assert reg.status_code == 201
    reg_data = reg.json()
    assert "access_token" in reg_data
    assert "token" in reg_data
    assert reg_data["token_type"] == "bearer"
    assert reg_data["user"]["name"] == "Kareem"
    assert reg_data["user"]["email"] == "kareem@example.com"
    assert "id" in reg_data["user"]

    # Verify password was hashed and NEVER stored in plaintext in the DB
    stored_user = db.get_user_by_email("kareem@example.com")
    assert stored_user is not None
    assert stored_user["password_hash"].startswith("pbkdf2_sha256$")
    assert "strongPassword123" not in stored_user["password_hash"]
    assert verify_password("strongPassword123", stored_user["password_hash"])

    # 2. Duplicate registration fails with 409
    dup = client.post("/auth/register", json={
        "name": "Kareem Duplicate",
        "email": "KAREEM@EXAMPLE.COM",  # case-insensitive check
        "password": "strongPassword123"
    })
    assert dup.status_code == 409
    assert dup.json()["detail"] == "An account with this email already exists."

    # 3. Registration with alternative field names (e.g. full_name)
    reg_alt = client.post("/auth/register", json={
        "full_name": "Laila Ali",
        "email": "laila@example.com",
        "password": "strongPassword123"
    })
    assert reg_alt.status_code == 201
    assert reg_alt.json()["user"]["name"] == "Laila Ali"

    # 4. Login with valid credentials
    login = client.post("/auth/login", json={
        "email": "kareem@example.com",
        "password": "strongPassword123"
    })
    assert login.status_code == 200
    login_data = login.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == "kareem@example.com"

    # 5. Login with 'username' field instead of 'email'
    login_user_field = client.post("/auth/login", json={
        "username": "kareem@example.com",
        "password": "strongPassword123"
    })
    assert login_user_field.status_code == 200
    assert login_user_field.json()["user"]["email"] == "kareem@example.com"

    # 6. Login with wrong password fails with 401
    wrong_pw = client.post("/auth/login", json={
        "email": "kareem@example.com",
        "password": "wrongPassword123"
    })
    assert wrong_pw.status_code == 401
    assert wrong_pw.json()["detail"] == "Incorrect email or password."

    # 7. Login with unknown email fails with 401
    unknown_user = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "strongPassword123"
    })
    assert unknown_user.status_code == 401
    assert unknown_user.json()["detail"] == "Incorrect email or password."


def test_api_auth_validation():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Empty name
    res = client.post("/auth/register", json={"name": "   ", "email": "valid@example.com", "password": "password123"})
    assert res.status_code == 422
    assert res.json()["detail"] == "Enter your name."

    # Invalid email format
    res = client.post("/auth/register", json={"name": "Valid", "email": "invalid-email", "password": "password123"})
    assert res.status_code == 422
    assert res.json()["detail"] == "Enter a valid email address."

    # Short password
    res = client.post("/auth/register", json={"name": "Valid", "email": "valid@example.com", "password": "short"})
    assert res.status_code == 422

    # Empty login credentials
    res = client.post("/auth/login", json={"email": "   ", "password": "password123"})
    assert res.status_code == 422


def test_api_protected_routes_and_me():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Register to get a valid token
    reg = client.post("/auth/register", json={"name": "Hana", "email": "hana@example.com", "password": "password123"})
    token = reg.json()["access_token"]

    # 1. /auth/me with valid token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Hana"
    assert me_res.json()["email"] == "hana@example.com"

    # 2. /auth/me with missing token
    assert client.get("/auth/me").status_code == 401

    # 3. /auth/me with invalid token
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"}).status_code == 401

    # 4. Protected route without auth
    assert client.get("/analysis/latest").status_code == 401

    # 5. Protected route with valid auth
    res_protected = client.get("/analysis/latest", headers={"Authorization": f"Bearer {token}"})
    assert res_protected.status_code == 404  # Valid token, but no analysis uploaded yet


def test_cors_preflight_and_credentials():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # Preflight OPTIONS request
    preflight = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        }
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert preflight.headers.get("access-control-allow-credentials") == "true"

