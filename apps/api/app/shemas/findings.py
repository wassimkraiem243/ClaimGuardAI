from pydantic import BaseModel, Field
from typing import Literal, Optional

class ValidationFindingDto(BaseModel):
    claimId: str = Field(..., description="Identifier of the validated claim")
    ruleId: str = Field(..., description="Identifier of the evaluated payer rule")
    severity: Literal['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] = Field(
        ..., description="Impact level of the rule violation"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Numerical confidence score between 0 and 1"
    )
    evidence: str = Field(..., description="Rule-linked evidence from claim data")
    suggestedAction: str = Field(..., description="Specific corrective action")
    explanation: Optional[str] = Field(None, description="Human-readable grounded explanation")