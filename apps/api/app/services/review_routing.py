from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.infrastructure.audit_log import REVIEW_ACTIONS, AuditError, log_review
from app.infrastructure.rule_engine.reporting.findings import build_report
from app.services import rule_validation

ReviewAction = Literal["confirm_issue", "dismiss_with_reason", "request_information", "mark_corrected_for_recheck"]


class QueueItem(BaseModel):
    claim_id: str
    rule_id: str
    status: str
    severity: str
    requires_human_review: bool
    explanation: str
    corrective_action: str
    priority: Literal["medium", "high"]


class RouteResponse(BaseModel):
    claim_id: str
    escalation_required: bool
    escalation_priority: Literal["none", "medium", "high"]
    escalation_reasons: list[str]
    queue: list[QueueItem]


class ReviewDecisionRequest(BaseModel):
    claim_id: str
    rule_id: str
    action: ReviewAction
    reason: str = Field(min_length=1, max_length=2000)
    original_status: str
    finding: Optional[dict[str, Any]] = None


def route_claim(claim: dict[str, Any]) -> RouteResponse:
    response = rule_validation.validate_envelope(claim)
    report = build_report(claim, response, rule_validation.get_policy_store())
    queue: list[QueueItem] = []
    for f in report.findings:
        if not f.requires_human_review:
            continue
        priority = "high" if f.status == "FAIL" and f.severity == "high" else "medium"
        queue.append(
            QueueItem(
                claim_id=f.claim_id,
                rule_id=f.rule_id,
                status=f.status,
                severity=f.severity,
                requires_human_review=True,
                explanation=f.explanation,
                corrective_action=f.corrective_action,
                priority=priority,
            )
        )
    esc = report.escalation
    return RouteResponse(
        claim_id=response.claim_id,
        escalation_required=esc.required,
        escalation_priority=esc.priority,
        escalation_reasons=esc.reasons,
        queue=queue,
    )


def submit_decision(actor: str, body: ReviewDecisionRequest) -> dict:
    if body.action not in REVIEW_ACTIONS:
        raise ValueError(f"unknown action: {body.action}")
    try:
        audit_path = str(settings.resolved_audit_log())
        _, seq = log_review(
            actor,
            body.action,
            body.claim_id,
            body.rule_id,
            body.reason,
            body.original_status,
            finding=body.finding,
            log=audit_path,
        )
    except AuditError as e:
        raise ValueError(str(e)) from e
    return {
        "recorded": True,
        "audit_seq": seq,
        "action": body.action,
        "claim_id": body.claim_id,
        "rule_id": body.rule_id,
    }
