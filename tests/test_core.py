import io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import docx
import pytest
from careerly_core import analyze_cv, analyze_file, CVError, NoRequirements, UnknownRole
from careerly_core.pipeline import jd_weights
from careerly_core.skills import extract_skills, catalog
from careerly_core.matcher import roles

CV = """Mariam Ahmed - Computer Science Student
SKILLS: Python, SQL, Microsoft Excel, Data Cleaning
EXPERIENCE
Data intern - 2 years of experience with Python and Pandas for data wrangling.
Built reports in Excel and wrote SQL queries (PostgreSQL) for sales analysis.
Projects: Used Python and Excel to analyse survey data, SQL for reporting. Git, C++ basics.
"""

JD = """Junior Backend Developer
We are looking for a developer to build REST APIs with Python and FastAPI.
Requirements: Python, FastAPI, PostgreSQL, Git. Experience with Docker is expected.
Nice to have: Redis, Kubernetes, React.
"""


def test_skill_extraction_and_ids():
    s = extract_skills(CV)
    assert {"Python", "SQL", "Excel", "Pandas", "PostgreSQL", "Git", "C++"} <= set(s)
    assert s["Python"]["mentions"] >= 3 and s["Python"]["level"] >= 80
    assert "Java" not in s and "Power BI" not in s
    assert all(isinstance(v["id"], int) for v in s.values())

def test_ids_are_unique_and_roles_use_known_skills():
    ids = [c["id"] for c in catalog().values()]
    assert len(ids) == len(set(ids))
    for role, d in roles().items():
        assert set(d["skills"]) <= set(catalog()), role

def test_no_false_positives_on_substrings():
    s = extract_skills("I like javascript and reactive design. Skills: C#, Node.js.")
    assert "Java" not in s and "React" not in s
    assert {"JavaScript", "C#", "Node.js"} <= set(s)

def test_jd_weights():
    w = jd_weights(JD)
    assert w["Python"] == 3            # mentioned twice -> high
    assert w["FastAPI"] == 3 and w["REST APIs"] == 2
    assert w["React"] == 1             # only under "Nice to have"
    assert "Kubernetes" not in w       # not in catalog (yet)

def test_jd_only_analysis():
    r = analyze_cv(CV, job_description=JD)
    by = {s["name"]: s for s in r["skills"]}
    assert by["Python"]["status"] == "matched"
    assert by["FastAPI"]["status"] == "missing"
    assert by["PostgreSQL"]["status"] == "matched"
    assert 0 < r["matchScore"] < 100
    assert "Docker" in r["missingSkills"]
    assert all("id" in s for s in r["skills"]) and r["cvSkills"]

def test_jd_without_known_skills():
    with pytest.raises(NoRequirements):
        analyze_cv(CV, job_description="We need a friendly person who likes dogs and sunshine.")

def test_role_mode_still_works():
    r = analyze_cv(CV, "data analyst intern")
    assert r["targetRole"] == "Data Analyst"
    by = {s["name"]: s for s in r["skills"]}
    assert by["SQL"]["status"] == "matched" and by["Power BI"]["status"] == "missing"
    with pytest.raises(UnknownRole):
        analyze_cv(CV, "Astronaut")

def test_implied_skill_gives_partial_credit():
    r = analyze_cv("Experienced with PostgreSQL and Tableau.", "Data Analyst")
    by = {s["name"]: s for s in r["skills"]}
    assert by["SQL"]["status"] == "gap" and by["SQL"]["level"] > 0
    assert by["Data Visualization"]["status"] == "gap"

def test_semantic_hook():
    r = analyze_cv("I know Python.", "Data Analyst", semantic_fn=lambda a, b: 0.9)
    assert any(s["status"] == "gap" for s in r["skills"])

def _docx_bytes(text):
    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()

def test_docx_upload():
    assert analyze_file(_docx_bytes(CV), "cv.docx", job_description=JD)["matchScore"] > 0

def test_pdf_upload():
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
    for line in CV.splitlines():
        c.drawString(40, y, line); y -= 16
    c.save()
    assert analyze_file(buf.getvalue(), "cv.pdf", job_description=JD)["matchScore"] > 0

def test_bad_files():
    with pytest.raises(CVError): analyze_file(b"hello", "cv.pdf", job_description=JD)        # fake pdf
    with pytest.raises(CVError): analyze_file(b"PK\x03\x04", "cv.exe", job_description=JD)   # wrong ext
    with pytest.raises(CVError): analyze_file(b"x", "cv.doc", job_description=JD)            # legacy doc
    with pytest.raises(CVError): analyze_file(_docx_bytes("hi"), "cv.docx", job_description=JD)  # empty
    with pytest.raises(CVError): analyze_file(b"%PDF-" + b"0" * (5 * 1024 * 1024), "cv.pdf", job_description=JD)  # >5MB
    with pytest.raises(CVError): analyze_file(b"%PDF-1.4 not really a pdf at all, just junk bytes", "cv.pdf", job_description=JD)
    with pytest.raises(CVError): analyze_file(b"PK\x03\x04junkjunkjunk", "cv.docx", job_description=JD)  # corrupt docx


def test_no_job_description_picks_best_role():
    r = analyze_cv(CV)                      # no role, no job description
    assert r["targetRole"] == r["roleFit"][0]["role"] == "Data Analyst"
    assert r["totalRequired"] > 0 and 0 < r["matchScore"] <= 100

def test_no_job_description_and_no_skills():
    with pytest.raises(CVError):
        analyze_cv("Experienced chef who loves cooking pasta and baking bread every day.")
