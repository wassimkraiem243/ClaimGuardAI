from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    return {
        "service": "ClaimGuard AI API",
        "docs": "/docs",
        "health": "/health",
        "ingest": "POST /claims/ingest (multipart file, header x-api-key)",
        "validate": "POST /v1/validate (JSON body, header x-api-key)",
    }


@router.get("/health")
def health():
    return {"status": "ok"}
