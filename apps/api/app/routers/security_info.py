from pathlib import Path

from fastapi import APIRouter, Depends

from app.deps import require_api_key

router = APIRouter(
    prefix="/v1/security",
    tags=["security"],
    dependencies=[Depends(require_api_key)],
)

_REPO_ROOT = Path(__file__).resolve().parents[4]


@router.get("/overview")
def security_overview():
    doc = _REPO_ROOT / "docs" / "security" / "PRIVACY_AND_SECURITY.md"
    text = doc.read_text(encoding="utf-8") if doc.exists() else ""
    return {
        "document": "docs/security/PRIVACY_AND_SECURITY.md",
        "markdown": text,
        "controls": {
            "upload_max_bytes": 5 * 1024 * 1024,
            "auth_modes": ["api_key", "reviewer_key", "jwt_bearer"],
            "roles": ["analyst", "auditor", "admin", "reviewer"],
            "audit_verify_path": "/v1/audit/verify",
            "fhir_preflight": True,
            "llm_clinical_guards": True,
        },
    }
