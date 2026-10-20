from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import require_api_key, require_authenticated, require_role
from app.routers import (
    analysis,
    audit,
    auth,
    claims,
    dashboard,
    findings,
    health,
    metrics,
    reviews,
    rules_catalog,
    validation,
)

app = FastAPI(title="ClaimGuard AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)

# Pack rule engine + HITL (API key — matches Phase 1 web flow)
app.include_router(validation.router)
app.include_router(rules_catalog.router)
app.include_router(reviews.router)

# Legacy CSV/FHIR ingest + evaluate (API key enforced on full app only)
app.include_router(claims.router, dependencies=[Depends(require_api_key)])

# Dashboard / LLM features (JWT + roles)
app.include_router(dashboard.router, dependencies=[Depends(require_authenticated)])
app.include_router(findings.router, dependencies=[Depends(require_role("analyst", "auditor"))])
app.include_router(metrics.router, dependencies=[Depends(require_authenticated)])
app.include_router(analysis.router)
app.include_router(audit.router, dependencies=[Depends(require_role("auditor"))])
