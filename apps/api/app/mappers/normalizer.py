"""Pure normalization helpers: no I/O, easy to unit-test."""
from datetime import datetime
from typing import Optional

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def norm_date(value: Optional[str]) -> Optional[str]:
    """Return ISO date or None. Unparseable -> ValueError (caller decides reject vs warn)."""
    if value is None or not value.strip():
        return None
    v = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {value!r}")


def norm_code(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    return value.strip().upper()


def norm_text(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    return value.strip()


_GENDER = {
    "m": "M",
    "f": "F",
    "male": "M",
    "female": "F",
    "other": "O",
    "unknown": "U",
    "o": "O",
    "u": "U",
}


def norm_gender(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    key = value.strip().lower()
    if len(key) == 1 and key.upper() in {"M", "F", "O", "U"}:
        return key.upper()
    return _GENDER.get(key)


def norm_number(value: Optional[str]) -> float:
    """Accepts '1 200,50' or '1200.50'. Raises ValueError if not numeric."""
    v = value.strip().replace(" ", "")
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    return float(v)