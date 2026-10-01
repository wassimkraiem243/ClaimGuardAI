"""Validate and normalize teaching envelopes (ClaimGuard pack v1.0.0)."""
from typing import Any

from app.domain.claim_package import IngestionRejected
from app.infrastructure.rule_engine.core.engine import IngestionError, check_envelope


def validate_and_seal(raw: dict[str, Any], *, claim_id: str | None = None) -> dict[str, Any]:
    """Return the envelope dict unchanged in values; raises IngestionRejected on transport errors."""
    cid = claim_id or raw.get("claim_id")
    try:
        check_envelope(raw)
    except IngestionError as e:
        raise IngestionRejected(str(e), field_path="envelope", claim_id=cid) from e
    return raw
