"""Step 4 - compare CV skills with what a role requires (gap analysis + score)."""
import difflib
import json
from typing import Callable, Optional

from .skills import DATA_DIR, catalog

MATCHED_AT = 50       # level >= this => "matched" (a single mention in the CV counts)
RELATED_LEVEL = 35    # level shown when we only have related evidence
RELATED_CREDIT = 0.5


class UnknownRole(ValueError):
    def __init__(self, role, available):
        self.available = available
        super().__init__(f"Unknown role '{role}'. Available: {', '.join(available)}")


def roles() -> dict:
    return json.loads((DATA_DIR / "roles.json").read_text(encoding="utf-8"))


def resolve_role(name: str) -> str:
    """Map free text ('data analyst intern') to a known role."""
    available = list(roles())
    low = name.strip().lower()
    for r in available:
        if low == r.lower():
            return r
    for r in available:
        if r.lower() in low:
            return r
    close = difflib.get_close_matches(low, [r.lower() for r in available], n=1, cutoff=0.6)
    if close:
        return next(r for r in available if r.lower() == close[0])
    raise UnknownRole(name, available)


def evaluate(cv_skills: dict, required: dict,
             semantic_fn: Optional[Callable[[str, str], float]] = None,
             semantic_threshold: float = 0.6) -> dict:
    """
    cv_skills: output of extract_skills
    required:  {skill_name: weight}
    semantic_fn: optional (a, b) -> similarity 0..1, e.g. sentence-transformers.
    """
    cat = catalog()
    rows, total, earned = [], 0.0, 0.0

    for name, weight in required.items():
        category = cat[name]["category"] if name in cat else "Other"
        total += weight

        if name in cv_skills:
            level = cv_skills[name]["level"]
            credit = min(level / MATCHED_AT, 1.0)
            status = "matched" if level >= MATCHED_AT else "gap"
            evidence = []
        else:
            evidence = [s for s in cv_skills if name in cat[s]["implies"]]
            if evidence:
                level, credit, status = RELATED_LEVEL, RELATED_CREDIT, "gap"
            else:
                level, credit, status = 0, 0.0, "missing"
                if semantic_fn and cv_skills:
                    best = max(cv_skills, key=lambda s: semantic_fn(name, s))
                    sim = semantic_fn(name, best)
                    if sim >= semantic_threshold:
                        level, credit, status = RELATED_LEVEL, sim * RELATED_CREDIT, "gap"
                        evidence = [best]

        earned += weight * credit
        rows.append({"id": cat[name]["id"], "name": name, "category": category, "level": level,
                     "status": status, "weight": weight, "evidence": evidence})

    score = round(100 * earned / total) if total else 0
    return {"score": score, "skills": rows}
