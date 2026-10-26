"""Quick test without the server:  python try_cv.py"""
import json
from careerly_core import analyze_file

with open("cv.pdf", "rb") as f:          # put any CV next to this file
    result = analyze_file(f.read(), "cv.pdf")   # optional: target_role="Backend Developer"

print(json.dumps(result, indent=2, ensure_ascii=False))
