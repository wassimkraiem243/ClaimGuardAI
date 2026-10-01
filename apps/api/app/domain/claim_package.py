"""Physical claim shape from legacy CSV/FHIR demo files (internal to legacy parsers).

Normalized API output is `NormalizedClaim` with the student-pack envelope in `envelope`."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Patient(BaseModel):
    id: str
    birth_date: Optional[str] = None  # ISO 8601
    gender: Optional[str] = None


class Encounter(BaseModel):
    id: str
    start: Optional[str] = None
    end: Optional[str] = None


class Coverage(BaseModel):
    policy_id: str
    payer_id: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class Provider(BaseModel):
    id: str
    npi: Optional[str] = None


class Diagnosis(BaseModel):
    code: str
    primary: bool = False


class ClaimLine(BaseModel):
    line_no: int
    procedure_code: str
    quantity: float
    amount: float
    currency: Optional[str] = None
    service_date: Optional[str] = None
    authorization_id: Optional[str] = None


class ClaimPackage(BaseModel):
    claim_id: str
    source: Literal["FHIR", "CSV"]
    patient: Patient
    encounter: Encounter
    coverage: Coverage
    provider: Provider
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    lines: list[ClaimLine]
    ingestion_warnings: list[str] = Field(default_factory=list)


class IngestionRejected(Exception):
    """Raised when input is structurally unusable. Audit logs this as INGESTION_REJECTED."""

    def __init__(self, reason: str, field_path: Optional[str] = None, claim_id: Optional[str] = None):
        self.reason, self.field_path, self.claim_id = reason, field_path, claim_id
        super().__init__(f"{reason}" + (f" [{field_path}]" if field_path else ""))

    def to_dict(self) -> dict:
        return {"event": "INGESTION_REJECTED", "reason": self.reason,
                "field_path": self.field_path, "claim_id": self.claim_id}