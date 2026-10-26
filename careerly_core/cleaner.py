"""Step 2 - normalise raw extracted text."""
import re
import unicodedata

_BULLETS = re.compile(r"[•●▪◦■►▶◆○·]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "")                 # soft hyphen
    text = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text)  # "data-\nbase" -> "database"
    text = _CONTROL.sub(" ", text)
    text = _BULLETS.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
