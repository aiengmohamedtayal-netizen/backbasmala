"""Step 3 - find skills in text using a curated catalog (no ML needed)."""
import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.I)


@lru_cache(maxsize=1)
def catalog() -> dict:
    """name -> {name, category, aliases, implies, pattern}"""
    items = json.loads((DATA_DIR / "skills.json").read_text(encoding="utf-8"))
    out = {}
    for it in items:
        aliases = sorted(set(it["aliases"] + [it["name"].lower()]), key=len, reverse=True)
        alt = "|".join(re.escape(a).replace(r"\ ", r"[\s\-]+") for a in aliases)
        # not glued to word chars, and "c" must not match "c++" etc.
        it["pattern"] = re.compile(rf"(?<![\w+#.])(?:{alt})(?![\w+#]|\.\w)", re.I)
        it.setdefault("implies", [])
        out[it["name"]] = it
    return out


def _level(mentions: int, has_years: bool) -> int:
    """Heuristic 0-100. More mentions + stated years => higher. Not a real assessment."""
    base = {1: 50, 2: 65, 3: 80}.get(mentions, 90)
    return min(95, base + (10 if has_years else 0))


def extract_skills(text: str) -> dict:
    """Return {skill_name: {name, category, mentions, level}} for skills found in text."""
    found = {}
    for name, it in catalog().items():
        matches = list(it["pattern"].finditer(text))
        if not matches:
            continue
        has_years = any(
            _YEARS.search(text[max(0, m.start() - 60): m.end() + 60]) for m in matches
        )
        found[name] = {
            "id": it["id"],
            "name": name,
            "category": it["category"],
            "mentions": len(matches),
            "level": _level(len(matches), has_years),
        }
    return found
