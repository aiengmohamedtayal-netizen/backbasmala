# AI Smart Career Analyzer — Backend API

Backend REST API for the **AI Smart Career Analyzer**, built with **FastAPI**, **SQLite (WAL mode)**, **PyJWT**, and **PBKDF2-HMAC-SHA256**. The backend handles user authentication, CV parsing (PDF and DOCX), skill matching against target job roles, gap analysis, dynamic learning roadmaps, and progress tracking.

---

## 1. Project Overview & Architecture

### Tech Stack
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Server:** [Uvicorn](https://www.uvicorn.org/) (ASGI)
- **Database:** SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL`)
- **Authentication:** JWT (JSON Web Tokens via [PyJWT](https://pyjwt.readthedocs.io/)) with Bearer token header
- **Password Security:** PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP recommended standard)
- **Document Parsing:** `pdfplumber` for PDF extraction, `python-docx` for Word documents

### Repository Architecture
```text
backend/
├── app/
│   ├── routes/
│   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   ├── cv.py          # /roles, /cv/upload, /analysis/latest
│   │   ├── learning.py    # PATCH /learning/progress
│   │   └── chat.py        # POST /chat (AI assistant placeholder)
│   ├── config.py          # Environment settings & configuration loading
│   ├── db.py              # Single isolated database access layer (SQLite WAL)
│   ├── deps.py            # FastAPI dependency injection (current_user Bearer auth)
│   ├── security.py        # PBKDF2 password hashing & PyJWT token utilities
│   └── views.py           # Presentation formatting & API payload transformations
├── careerly_core/         # Pure domain logic (independent of web framework)
│   ├── data/              # Static dictionaries: roles.json, skills.json, courses.json
│   ├── parser.py          # PDF & DOCX text extraction
│   ├── cleaner.py         # Text sanitization and normalization
│   ├── skills.py          # Skill extraction engine
│   ├── matcher.py         # Job description & role scoring engine
│   ├── roadmap.py         # Step-by-step learning roadmap generator
│   └── pipeline.py        # Core end-to-end analysis orchestrator
├── tests/
│   ├── test_app.py        # Auth flow, security, DB, and API integration tests
│   └── test_core.py       # CV parser, skills extraction, and matching tests
├── main.py                # Application entrypoint & CORS middleware
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development & testing dependencies
├── .env.example           # Environment variable template
└── README.md              # Project documentation
```

---

## 2. Prerequisites

- **Python:** 3.10, 3.11, 3.12, or 3.13
- **Git**

---

## 3. Installation & Environment Setup

### Step 1: Clone the repository
```bash
git clone https://github.com/aiengmohamedtayal-netizen/backbasmala.git
cd backbasmala
```

### Step 2: Create and activate a Virtual Environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env      # Windows PowerShell
# or: cp .env.example .env  # Linux / macOS
```

Generate a secure `SECRET_KEY` using Python:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env` and set the generated key:
```env
SECRET_KEY=your-generated-secret-key-here
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
TOKEN_DAYS=7
```

> **Security Note:** The `.env` file contains sensitive configuration and is explicitly ignored by `.gitignore`. Never commit `.env` to version control.

---

## 4. Database Setup & Management

- **Engine:** SQLite 3 (Standard Library — zero external database server required to run locally).
- **Initialization:** Database tables are created automatically on startup by calling `init_db()` in `main.py`.
- **Location:** By default, stored at `careerly.db` in the repository root (customizable via `DATABASE_PATH` in `.env`).
- **Resetting Database:** To start with a completely fresh database, simply delete `careerly.db`:
  ```powershell
  Remove-Item careerly.db -ErrorAction SilentlyContinue
  ```
  The database and its schema will be recreated automatically the next time the server starts.

---

## 5. Running the Application

Start the development server with live-reload:
```bash
python -m uvicorn main:app --reload --port 8000
```

Once running:
- **API Base URL:** `http://127.0.0.1:8000`
- **Interactive OpenAPI Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
- **Alternative Documentation (ReDoc):** `http://127.0.0.1:8000/redoc`

---

## 6. API Documentation

### Public Endpoints

#### `GET /`
Health check endpoint.
- **Auth:** None
- **Response (200 OK):**
  ```json
  {
    "message": "AI Smart Career Analyzer is running!"
  }
  ```

#### `POST /auth/register`
Create a new user account. Passwords are automatically hashed with PBKDF2 before storage.
- **Auth:** None
- **Request Body (`application/json`):**
  ```json
  {
    "name": "Sarah Connor",
    "email": "sarah@example.com",
    "password": "SecurePassword123"
  }
  ```
  *(Accepts `name`, `full_name`, or `username` for the user's display name)*.
- **Responses:**
  - `201 Created`: Account created successfully.
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "token": "eyJhbGciOi...",
      "token_type": "bearer",
      "user": {
        "id": 1,
        "name": "Sarah Connor",
        "email": "sarah@example.com"
      }
    }
    ```
  - `409 Conflict`: Email already registered.
  - `422 Unprocessable Content`: Validation failure (e.g. invalid email format, password shorter than 8 characters).

#### `POST /auth/login`
Authenticate with email and password to receive a Bearer JWT.
- **Auth:** None
- **Request Body (`application/json`):**
  ```json
  {
    "email": "sarah@example.com",
    "password": "SecurePassword123"
  }
  ```
  *(Accepts `email` or `username`)*.
- **Responses:**
  - `200 OK`: Successful authentication (returns `access_token`, `token_type: "bearer"`, and `user`).
  - `401 Unauthorized`: `"Incorrect email or password."` (protected against timing attacks with constant-time verification).
  - `422 Unprocessable Content`: Missing credentials.

#### `GET /roles`
List all predefined target career roles available for CV matching.
- **Auth:** None
- **Response (200 OK):**
  ```json
  {
    "roles": [
      "Backend Developer",
      "Frontend Developer",
      "Fullstack Developer",
      "Data Analyst",
      "Machine Learning Engineer",
      "DevOps Engineer"
    ]
  }
  ```

---

### Authenticated Endpoints (`Authorization: Bearer <token>`)

Include the access token in the request header:
```text
Authorization: Bearer eyJhbGciOi...
```

#### `GET /auth/me`
Retrieve the authenticated user's profile and verify session validity.
- **Auth:** Required (`Bearer`)
- **Response (200 OK):**
  ```json
  {
    "id": 1,
    "name": "Sarah Connor",
    "email": "sarah@example.com"
  }
  ```
- **Error (401 Unauthorized):** Missing or expired token.

#### `POST /cv/upload`
Upload a CV file (PDF or DOCX) to analyze skills, compute match score, and generate a customized roadmap.
- **Auth:** Required (`Bearer`)
- **Request Format:** `multipart/form-data`
  - `file`: Binary file (`.pdf` or `.docx`, max 5MB)
  - `target_role`: (Optional string) Target role name. If empty, the engine infers the closest matching role from the CV.
- **Response (200 OK):**
  ```json
  {
    "match_score": 78,
    "target_role": "Backend Developer",
    "existing_skills": [
      { "id": 1, "name": "Python", "category": "Languages" }
    ],
    "missing_skills": [
      { "id": 12, "name": "Docker", "category": "DevOps", "priority": "high" }
    ],
    "roadmap": [
      {
        "skill_id": 12,
        "skill": "Docker",
        "status": "todo",
        "resources": [
          { "title": "Docker Tutorial for Beginners", "type": "youtube", "url": "https://..." }
        ]
      }
    ],
    "jobs": []
  }
  ```

#### `GET /analysis/latest`
Fetch the most recent CV analysis and roadmap for the logged-in user.
- **Auth:** Required (`Bearer`)
- **Responses:**
  - `200 OK`: Analysis object merged with user's saved roadmap progress.
  - `404 Not Found`: No analysis uploaded yet.

#### `PATCH /learning/progress`
Update the completion status of a roadmap skill for the current user.
- **Auth:** Required (`Bearer`)
- **Request Body (`application/json`):**
  ```json
  {
    "skill_id": 12,
    "status": "in_progress"
  }
  ```
  *(Valid statuses: `"todo"`, `"in_progress"`, `"done"`)*.
- **Response (200 OK):** `{"ok": true}`

#### `POST /chat`
AI Career Assistant endpoint (placeholder).
- **Auth:** Required (`Bearer`)
- **Response (503 Service Unavailable):** Returns informative status message until LLM provider (Groq / Gemini) is connected.

---

## 7. Running Tests

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Run the complete test suite:
```bash
python -m pytest -v tests
```

### Test Coverage Highlights
- **`tests/test_app.py`:**
  - `test_password_hashing`: PBKDF2 salt randomness, correct hashing format, constant-time verification.
  - `test_tokens`: JWT issuance, secret validation, expiration, and algorithm tampering immunity.
  - `test_users`: Database CRUD operations and email uniqueness constraints.
  - `test_analysis_and_progress_flow`: Analysis persistence, serialization, and per-user roadmap progress upsert.
  - `test_api_auth_flow`: End-to-end registration, password non-plaintext verification in DB, login, duplicate rejection, and profile lookup.
  - `test_api_auth_validation`: Form validation rules for email, names, and minimum password lengths.
  - `test_api_protected_routes_and_me`: Session validation on `/auth/me` and `/analysis/latest`.
  - `test_cors_preflight_and_credentials`: CORS preflight header validation.
- **`tests/test_core.py`:**
  - Skill extraction, alias resolution, substring false-positive protection, role weighting, DOCX parsing, and bad file handling.

---

## 8. Deployment & Known Considerations

1. **CORS Origins:** When deploying to production, update `CORS_ORIGINS` in your environment to match your deployed frontend domain (e.g. `https://your-frontend.vercel.app`).
2. **Database Migration to PostgreSQL:** The storage layer is strictly isolated in [`app/db.py`](app/db.py). When transitioning to hosted PostgreSQL (e.g. Supabase, Neon, or Cloud SQL), only `app/db.py` needs connection string updates — no route handlers or business logic require changes.
3. **Optional PDF Generation Test:** In `test_core.py`, `test_pdf_upload` is safely skipped if `reportlab` is not installed; it does not affect runtime application parsing, which uses `pdfplumber`.
