"""Glue: CV (file or text) + job description (or role) -> analysis dict."""
import re
from typing import Callable, Optional

from .cleaner import clean_text
from .matcher import UnknownRole, evaluate, resolve_role, roles
from .parser import CVError, extract_text
from .skills import extract_skills


class NoRequirements(CVError):
    """The job description has no skills we recognise."""


# Everything after one of these phrases is treated as optional (weight 1).
_OPTIONAL = re.compile(
    r"nice[\s-]to[\s-]have|good[\s-]to[\s-]have|bonus points|\ba plus\b|"
    r"preferred (?:qualifications|skills|experience)|desirable",
    re.I,
)


def jd_weights(text: str) -> dict:
    """Skill -> importance from a pasted job description.
    3 = mentioned 2+ times, 2 = mentioned once, 1 = only in a 'nice to have' part."""
    text = clean_text(text)
    m = _OPTIONAL.search(text)
    head, tail = (text[:m.start()], text[m.start():]) if m else (text, "")
    weights = {n: (3 if s["mentions"] >= 2 else 2) for n, s in extract_skills(head).items()}
    for n in extract_skills(tail):
        weights.setdefault(n, 1)
    return weights


def analyze_cv(cv_text: str, target_role: Optional[str] = None,
               job_description: Optional[str] = None,
               semantic_fn: Optional[Callable[[str, str], float]] = None) -> dict:
    cv_skills = extract_skills(clean_text(cv_text))
    has_jd = bool(job_description and job_description.strip())

    role_fit = sorted(
        ({"role": r, "score": evaluate(cv_skills, d["skills"], semantic_fn)["score"]}
         for r, d in roles().items()),
        key=lambda x: -x["score"],
    )

    required, role_name = {}, None
    if target_role and target_role.strip():
        try:
            role_name = resolve_role(target_role)
            required.update(roles()[role_name]["skills"])
        except UnknownRole:
            if not has_jd:
                raise
    if has_jd:
        for name, w in jd_weights(job_description).items():
            required[name] = max(required.get(name, 0), w)
    if not required and not has_jd and not (target_role and target_role.strip()):
        # No job description and no chosen role: compare against the closest role.
        if not cv_skills:
            raise CVError("We could not find any known skills in this CV. "
                          "Add a skills section and try again.")
        role_name = role_fit[0]["role"]
        required.update(roles()[role_name]["skills"])
    if not required:
        raise NoRequirements(
            "We could not find any known skills in this job description. "
            "Paste the full requirements section and try again.")

    result = evaluate(cv_skills, required, semantic_fn)
    rows = sorted(result["skills"], key=lambda r: -r["weight"])

    return {
        "targetRole": role_name,
        "matchScore": result["score"],
        "skills": rows,                                   # required skills + status
        "cvSkills": [{k: s[k] for k in ("id", "name", "category", "level")}
                     for s in cv_skills.values()],        # everything found in the CV
        "missingSkills": [r["name"] for r in rows if r["status"] != "matched"],
        "matchedCount": sum(r["status"] == "matched" for r in rows),
        "totalRequired": len(rows),
        "roleFit": role_fit,
    }


def analyze_file(data: bytes, filename: str, target_role: Optional[str] = None,
                 job_description: Optional[str] = None, **kw) -> dict:
    return analyze_cv(extract_text(data, filename), target_role, job_description, **kw)
