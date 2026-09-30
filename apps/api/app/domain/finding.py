from typing import Literal, Optional
from pydantic import BaseModel, Field

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ValidationFinding(BaseModel):
    """Structured output required by the brief: claim, rule, evidence, severity, confidence, action."""
    claim_id: str
    rule_id: str
    rule_name: str = ""
    category: str = ""       # missing | inconsistent | duplicate | unsupported
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    evidence: str            # cites the ClaimPackage field path and value
    suggested_action: str
    line_no: Optional[int] = None