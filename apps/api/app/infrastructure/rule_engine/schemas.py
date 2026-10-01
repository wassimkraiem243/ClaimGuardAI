from typing import Any, Optional

from pydantic import BaseModel

from app.infrastructure.rule_engine.domain.policy import Policy
from app.infrastructure.rule_engine.domain.result import ValidationResponse


class PreviousRun(BaseModel):
    run_id: str
    input_hash: str


class ValidateRequest(BaseModel):
    claim: dict[str, Any]
    policy_override: Optional[Policy] = None
    previous_run: Optional[PreviousRun] = None


class BatchRequest(BaseModel):
    claims: list[Any]
    policy_override: Optional[Policy] = None


class IngestionErrorItem(BaseModel):
    index: int
    claim_id: Optional[str] = None
    message: str
    details: list[dict] = []


class BatchResponse(BaseModel):
    results: list[ValidationResponse]
    ingestion_errors: list[IngestionErrorItem]
