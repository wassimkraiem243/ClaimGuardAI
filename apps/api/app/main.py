from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import claims
from app.routers import analysis, dashboard, findings, health, metrics, rules_catalog, validation

app = FastAPI(title="ClaimGuard AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(findings.router)
app.include_router(metrics.router)
app.include_router(analysis.router)
app.include_router(claims.router)
app.include_router(validation.router)
app.include_router(rules_catalog.router)

