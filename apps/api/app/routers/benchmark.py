import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import require_api_key

router = APIRouter(
    prefix="/v1/benchmark",
    tags=["benchmark"],
    dependencies=[Depends(require_api_key)],
)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _metrics_path() -> Path:
    return _REPO_ROOT / "docs" / "evaluation" / "metrics.json"


def _load_metrics() -> list:
    path = _metrics_path()
    if not path.exists():
        raise HTTPException(404, "metrics.json not found; run make_eval_report.py")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("")
def list_benchmarks():
    return _load_metrics()


@router.get("/report/summary")
def evaluation_report_summary(
    split: str = Query("validation", description="Challenge hold-out: validation (50 claims)"),
):
    path = _REPO_ROOT / "docs" / "evaluation" / "EVALUATION_REPORT.md"
    summary = {"split": split, "report_path": "docs/evaluation/EVALUATION_REPORT.md"}
    try:
        rows = _load_metrics()
    except HTTPException:
        rows = []
    for row in rows:
        if row.get("split") == split:
            summary["metrics"] = {
                "n_claims": row.get("n_claims"),
                "macro_f1": row.get("macro_f1"),
                "micro_f1": row.get("micro", {}).get("f1"),
                "false_alarm_rate": row.get("micro", {}).get("false_alarm_rate"),
                "status_accuracy": row.get("status_accuracy"),
                "latency_ms": row.get("latency_ms"),
                "claim_exact_match": row.get("claim_exact_match"),
            }
            break
    summary["report_available"] = path.exists()
    return summary


@router.get("/splits/{split}")
def get_benchmark_split(split: str):
    rows = _load_metrics()
    for row in rows:
        if row.get("split") == split:
            return row
    raise HTTPException(404, f"unknown split: {split}")
