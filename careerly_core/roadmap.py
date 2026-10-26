"""Step 5 - learning resources for each skill gap (no external API needed)."""
import json
from urllib.parse import quote_plus

from .skills import DATA_DIR


def _courses() -> dict:
    return json.loads((DATA_DIR / "courses.json").read_text(encoding="utf-8"))


def resources_for(skill: str) -> list:
    """Official tutorial (when we have one) + a YouTube search link (always valid)."""
    out = []
    official = _courses().get(skill)
    if official:
        out.append({"title": official["title"], "type": "docs", "url": official["url"]})
    q = quote_plus(f"{skill} tutorial for beginners")
    out.append({
        "title": f"{skill} tutorials for beginners",
        "type": "youtube",
        "url": f"https://www.youtube.com/results?search_query={q}",
    })
    return out


def build_roadmap(gap_rows: list, limit: int = 8) -> list:
    """gap_rows must already be sorted by importance."""
    return [
        {"skill_id": r["id"], "skill": r["name"], "resources": resources_for(r["name"])}
        for r in gap_rows[:limit]
    ]
