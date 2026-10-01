"""JSONL: one teaching envelope per line (authoritative pack format)."""
import json

from app.domain.claim_package import IngestionRejected
from app.domain.normalized_claim import NormalizedClaim
from app.mappers.envelope import validate_and_seal


class JsonlEnvelopeParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise IngestionRejected("File is not valid UTF-8 text")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            raise IngestionRejected("JSONL file is empty")
        out: list[NormalizedClaim] = []
        for n, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                raise IngestionRejected("Invalid JSON on line", field_path=f"line {n}")
            if not isinstance(obj, dict):
                raise IngestionRejected("Each JSONL line must be an object", field_path=f"line {n}")
            envelope = validate_and_seal(obj, claim_id=obj.get("claim_id"))
            out.append(NormalizedClaim(envelope=envelope, source="JSONL"))
        return out
