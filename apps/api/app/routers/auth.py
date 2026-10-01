from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import security
from app.infrastructure.repositories.postgres_users import PostgresUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])
TOKEN_TTL = 3600
_DUMMY_HASH = security.hash_password("not-a-real-password")  # keeps timing equal for unknown users


def get_user_repository():
    return PostgresUserRepository()


@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user_repository().get(form.username)
    ok = security.verify_password(form.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok or user["disabled"]:  # one message for every failure: no user enumeration
        raise HTTPException(401, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": security.create_token(user["username"], user["role"], TOKEN_TTL),
            "token_type": "bearer", "expires_in": TOKEN_TTL}