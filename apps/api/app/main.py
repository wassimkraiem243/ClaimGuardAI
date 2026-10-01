from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import require_authenticated, require_role
from app.routers import analysis, audit, auth, claims, dashboard, findings, health, metrics

app = FastAPI(title="ClaimGuard AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public
app.include_router(health.router)
app.include_router(auth.router)  # prefix "/auth" is already inside auth.py

# Protected (deny by default)
app.include_router(claims.router,    dependencies=[Depends(require_role("analyst"))])
app.include_router(audit.router,     dependencies=[Depends(require_role("auditor"))])
app.include_router(findings.router,  dependencies=[Depends(require_role("analyst", "auditor"))])
app.include_router(dashboard.router, dependencies=[Depends(require_authenticated)])
app.include_router(metrics.router,   dependencies=[Depends(require_authenticated)])
app.include_router(analysis.router)  # protected per route in analysis.py