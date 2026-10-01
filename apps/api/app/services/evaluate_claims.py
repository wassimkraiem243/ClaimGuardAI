from typing import Callable

from app.domain.claim_package import ClaimPackage
from app.domain.finding import ValidationFinding
from app.domain.rules import RULES, BatchContext, RuleConfig

_SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class EvaluateClaims:
    """Use case: run the enabled catalogue rules over normalized claims."""

    def __init__(self, catalogue: list[RuleConfig], registry: dict[str, Callable] = RULES):
        unknown = [r.id for r in catalogue if r.id not in registry]
        if unknown:  # config error: fail loudly, never skip silently
            raise ValueError(f"Catalogue references unknown rules: {unknown}")
        self._rules = [r for r in catalogue if r.enabled]
        self._registry = registry

    def execute(self, claims: list[ClaimPackage], known: dict | None = None) -> list[ValidationFinding]:
        ctx, out = BatchContext(claims, known), []
        for c in claims:
            for cfg in self._rules:
                for evidence, line_no in self._registry[cfg.id](c, cfg.params, ctx):
                    out.append(ValidationFinding(
                        claim_id=c.claim_id, rule_id=cfg.id, rule_name=cfg.name, category=cfg.category,
                        severity=cfg.severity, confidence=cfg.confidence, evidence=evidence,
                        suggested_action=cfg.suggested_action, line_no=line_no))
        out.sort(key=lambda f: (_SEV_ORDER[f.severity], f.claim_id, f.line_no or 0))
        return out