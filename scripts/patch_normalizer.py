"""Normalizer fixes: numbers that overflow to inf, Excel date-time strings.
Safe to re-run. Run from the repo root:  python scripts/patch_normalizer.py"""
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "apps" / "api" / "app" / "mappers" / "normalizer.py"
EDITS = [
    ("import math", "import re\n", "import math\nimport re\n"),
    ("date-time strings",
     '    if "T" in v:\n        v = v.split("T", 1)[0]\n',
     '    v = v.split("T", 1)[0].split(" ", 1)[0]  # drop a time part: ISO "T" or the space Excel uses\n'),
    ("finite numbers only",
     "    return float(v)\n",
     "    f = float(v)\n    if not math.isfinite(f):  # a 400-digit string converts to inf\n"
     '        raise ValueError(f"number out of range: {value[:20]!r}")\n    return f\n'),
]

text = PATH.read_text(encoding="utf-8")
for label, old, new in EDITS:
    if new in text:
        print(f"  already applied  {label}")
    elif text.count(old) == 1:
        text = text.replace(old, new)
        print(f"  patched          {label}")
    else:
        print(f"  NOT FOUND ({text.count(old)} matches)  {label}  -> send me the file")
PATH.write_text(text, encoding="utf-8", newline="\n")