import os
from pathlib import Path

# apps/api/app/infrastructure/rule_engine/config.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
RULES_DIR = Path(os.getenv("RULES_DIR", REPO_ROOT / "data" / "payer-rules"))
MAX_BATCH = int(os.getenv("MAX_BATCH", "1000"))
