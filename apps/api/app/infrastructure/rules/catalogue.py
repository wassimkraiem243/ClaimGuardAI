import json
import os
from pathlib import Path

from app.domain.rules import RuleConfig

# .../apps/api/app/infrastructure/rules/catalogue.py -> repo root is parents[5]
DEFAULT_PATH = Path(__file__).resolve().parents[5] / "data" / "payer-rules" / "catalogue.json"


def load_catalogue(path: str | os.PathLike | None = None) -> list[RuleConfig]:
    """Read the rule catalogue on every call, so editing the JSON takes effect without a restart."""
    p = Path(path or os.environ.get("CLAIMGUARD_RULES_PATH") or DEFAULT_PATH)
    data = json.loads(p.read_text(encoding="utf-8"))
    rules = [RuleConfig(**r) for r in data["rules"]]
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate rule ids in catalogue")
    return rules