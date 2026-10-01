"""Teaching claim envelope v1.0.0 — normalized output of ingestion (student pack contract)."""
from typing import Any, Literal

from pydantic import BaseModel, Field

ClaimEnvelope = dict[str, Any]


class NormalizedClaim(BaseModel):
    """Immutable normalized claim for rules, audit, and UI. Rules read `envelope` verbatim."""

    envelope: ClaimEnvelope
    source: Literal["JSONL", "PACK_CSV", "FHIR_PACK", "CSV_LEGACY", "FHIR_LEGACY"]
    ingestion_warnings: list[str] = Field(default_factory=list)
