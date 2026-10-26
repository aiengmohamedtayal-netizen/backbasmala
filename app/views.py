"""Turns the core result into the exact JSON shape the frontend expects (see src/api.js)."""
from careerly_core import build_roadmap

_PRIORITY = {3: "high", 2: "medium"}  # anything else -> "low"
VALID_STATUS = ("todo", "in_progress", "done")


def to_api(result: dict) -> dict:
    """Saved in the DB. Roadmap statuses are NOT stored here (they live in `progress`)."""
    gaps = [r for r in result["skills"] if r["status"] != "matched"]
    gaps.sort(key=lambda r: (-r["weight"], r["status"] != "missing"))  # important + missing first
    return {
        "match_score": result["matchScore"],
        "target_role": result.get("targetRole"),
        "existing_skills": [
            {"id": s["id"], "name": s["name"], "category": s["category"]} for s in result["cvSkills"]
        ],
        "missing_skills": [
            {"id": r["id"], "name": r["name"], "category": r["category"],
             "priority": _PRIORITY.get(r["weight"], "low")}
            for r in gaps
        ],
        "roadmap": build_roadmap(gaps),
        "jobs": [],  # Step 5: real jobs (Remotive / RemoteOK)
    }


def with_progress(payload: dict, progress: dict) -> dict:
    """Adds each roadmap item's saved status (default 'todo')."""
    return {
        **payload,
        "roadmap": [{**item, "status": progress.get(item["skill_id"], "todo")}
                    for item in payload["roadmap"]],
    }
