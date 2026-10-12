from fastapi import FastAPI
from app.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.routers import claims
from app.routers import analysis, dashboard, findings, health, metrics, reviews, rules_catalog, validation

app = FastAPI(title="ClaimGuard AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
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
app.include_router(reviews.router)

