import os
from functools import lru_cache
from typing import Any, Optional

from app.config import settings
from app.infrastructure.rule_engine.audit_hook import AuditError, audited_validate
from app.infrastructure.rule_engine.config import MAX_BATCH
from app.infrastructure.rule_engine.core.engine import IngestionError
from app.infrastructure.rule_engine.domain.policy import Policy
from app.infrastructure.rule_engine.domain.result import ValidationResponse
from app.infrastructure.rule_engine.schemas import BatchResponse, IngestionErrorItem
from app.infrastructure.rule_engine.stores.policy_store import PolicyStore


@lru_cache(maxsize=1)
def get_policy_store() -> PolicyStore:
    return PolicyStore.from_dir(settings.resolved_rules_dir())


def _apply_audit_env() -> None:
    os.environ["AUDIT_ENABLED"] = "1" if settings.audit_enabled else "0"
    os.environ["AUDIT_LOG"] = str(settings.resolved_audit_log())
    os.environ["RULES_DIR"] = str(settings.resolved_rules_dir())


def validate_envelope(
    claim: dict[str, Any],
    policy_override: Optional[Policy] = None,
    previous_run: Optional[tuple[str, str]] = None,
) -> ValidationResponse:
    _apply_audit_env()
    store = get_policy_store()
    return audited_validate(
        claim,
        store,
        policy_override,
        source="api:/v1/validate",
        previous_run=previous_run,
    )


def validate_batch(
    claims: list[Any],
    policy_override: Optional[Policy] = None,
) -> BatchResponse:
    if len(claims) > min(MAX_BATCH, settings.rule_engine_max_batch):
        raise ValueError(f"batch exceeds {min(MAX_BATCH, settings.rule_engine_max_batch)} claims")
    _apply_audit_env()
    store = get_policy_store()
    results: list[ValidationResponse] = []
    errors: list[IngestionErrorItem] = []
    for i, raw in enumerate(claims):
        try:
            results.append(
                audited_validate(
                    raw,
                    store,
                    policy_override,
                    source=f"api:/v1/validate/batch[{i}]",
                )
            )
        except IngestionError as e:
            cid = raw.get("claim_id") if isinstance(raw, dict) else None
            errors.append(
                IngestionErrorItem(index=i, claim_id=cid, message=str(e), details=e.details)
            )
    return BatchResponse(results=results, ingestion_errors=errors)


def list_rules_catalog() -> list[dict]:
    store = get_policy_store()
    return [
        {
            "rule_id": m.rule_id,
            "title": m.title,
            "severity": m.severity,
            "version": m.version,
            "source": m.source,
            "logic": m.logic,
            "corrective_action": m.corrective_action,
        }
        for m in store.rules.values()
    ]


def get_policy(policy_id: str) -> Optional[Policy]:
    return get_policy_store().get(policy_id)
