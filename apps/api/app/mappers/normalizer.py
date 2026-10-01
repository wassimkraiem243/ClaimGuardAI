"""Pure normalization helpers: no I/O, easy to unit-test."""
import math
import re
from datetime import datetime
from typing import Optional

# Day-first formats are intentional (Tunisian / French exports): 02/06/2026 is 2 June.
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y")
MAX_ABS = 1e18  # sanity cap: far above any real claim amount
_NUMBER = re.compile(r"^[+-]?\d+(\.\d+)?$")
_SPACES = re.compile(r"[\s\u00a0\u202f]")  # regular, no-break and narrow no-break spaces


def norm_date(value: Optional[str]) -> Optional[str]:
    """Return ISO date or None. Unparseable -> ValueError (caller decides reject vs warn).
    A time part (2026-05-02T10:30:00) is dropped: the claim model stores dates only."""
    if value is None or not value.strip():
        return None
    v = value.strip()
    v = v.split("T", 1)[0].split(" ", 1)[0]  # drop a time part: ISO "T" or the space Excel uses
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


def norm_number(value: Optional[str]) -> float:
    """Accepts '1200.50', '1200,50', '1 200,50', '1,200.50', '1.200,50'.
    When both separators appear, the LAST one is the decimal point.
    Rejects nan, inf, exponents and anything else that is not a plain decimal number."""
    if value is None:
        raise ValueError("missing number")
    v = _SPACES.sub("", value)
    if "," in v and "." in v:
        dec = "," if v.rfind(",") > v.rfind(".") else "."
        thou = "." if dec == "," else ","
        v = v.replace(thou, "").replace(dec, ".")
    elif "," in v:
        # '1,200,000' is a thousands separator; a single comma is a decimal comma ('200,00')
        v = v.replace(",", "") if v.count(",") > 1 else v.replace(",", ".")
    if not _NUMBER.match(v):
        raise ValueError(f"not a plain decimal number: {value!r}")
    result = float(v)
    if not math.isfinite(result) or abs(result) > MAX_ABS:
        raise ValueError(f"number out of range: {value!r}")
    return result