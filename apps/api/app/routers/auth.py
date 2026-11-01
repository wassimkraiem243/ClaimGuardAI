from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError

from app import security
from app.infrastructure.repositories.postgres_users import PostgresUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])
TOKEN_TTL = 3600
_DUMMY_HASH = security.hash_password("not-a-real-password")  # keeps timing equal for unknown users


def get_user_repository():
    return PostgresUserRepository()


@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    try:
        user = get_user_repository().get(form.username)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_unavailable",
                "message": "Cannot reach PostgreSQL for login. Start docker compose and run migrations.",
            },
        ) from e
    ok = security.verify_password(form.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok or user["disabled"]:  # one message for every failure: no user enumeration
        raise HTTPException(401, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    try:
        token = security.create_token(user["username"], user["role"], TOKEN_TTL)
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "jwt_not_configured",
                "message": str(e),
            },
        ) from e
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": TOKEN_TTL,
    }