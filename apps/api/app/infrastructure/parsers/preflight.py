"""Input hardening that runs BEFORE the real parsers: bytes in, clean bytes out, or InputRejected.
Keeps messy real-world files (French Excel, BOM, bad JSON) from reaching the domain parsers."""
import csv
import io
import json
import re
from typing import Optional

_DELIMS = [",", ";", "\t", "|"]
_DECIMAL_COMMA = re.compile(r"^\s*-?\d+,\d+\s*$")


class InputRejected(Exception):
    """Same JSON shape as IngestionRejected so clients handle one error format."""

    def __init__(self, reason: str, field_path: str, claim_id: Optional[str] = None):
        super().__init__(reason)
        self.reason, self.field_path, self.claim_id = reason, field_path, claim_id

    def to_dict(self) -> dict:
        return {"event": "INGESTION_REJECTED", "reason": self.reason,
                "field_path": self.field_path, "claim_id": self.claim_id}


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")  # also strips the BOM
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")  # legacy Excel exports


def prepare_csv(raw: bytes) -> bytes:
    text = _decode(raw)
    if not text.strip():
        raise InputRejected("Empty file", "file")
    header = next(line for line in text.splitlines() if line.strip())
    delim = max(_DELIMS, key=header.count) if any(d in header for d in _DELIMS) else ","
    try:
        rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    except csv.Error as e:
        raise InputRejected(f"Malformed CSV: {e}", "file")
    if len(rows) < 2:
        raise InputRejected("CSV has a header but no data rows", "file")
    rows[0] = [h.strip() for h in rows[0]]
    if delim != ",":  # decimal commas are only unambiguous when the delimiter is not a comma
        rows[1:] = [[c.strip().replace(",", ".") if _DECIMAL_COMMA.match(c) else c for c in r] for r in rows[1:]]
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue().encode("utf-8")


def check_fhir(raw: bytes) -> bytes:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputRejected("File is not valid UTF-8", "file")
    if not text.strip():
        raise InputRejected("Empty file", "file")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise InputRejected(f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}", "file")
    except RecursionError:
        raise InputRejected("JSON is nested too deeply", "file")
    rtype = doc.get("resourceType") if isinstance(doc, dict) else None
    if rtype != "Bundle":
        raise InputRejected(f"Expected a FHIR Bundle, got resourceType={rtype!r}", "resourceType")
    entries = doc.get("entry")
    has_claim = isinstance(entries, list) and any(
        isinstance(e, dict) and isinstance(e.get("resource"), dict)
        and e["resource"].get("resourceType") == "Claim" for e in entries)
    if not has_claim:
        raise InputRejected("Bundle contains no Claim resource", "Bundle.entry[].resource")
    return text.encode("utf-8")


def reject_duplicate_ids(claims) -> None:
    seen, dups = set(), []
    for c in claims:
        if c.claim_id in seen and c.claim_id not in dups:
            dups.append(c.claim_id)
        seen.add(c.claim_id)
    if dups:
        raise InputRejected(f"Duplicate claim_id in upload: {dups}", "claim_id", dups[0])