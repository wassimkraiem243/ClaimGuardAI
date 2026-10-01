import os

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")


# --- Ancien mécanisme (à retirer quand plus aucun routeur ne l'importe) ---
def require_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


# --- JWT + rôles ---
def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2)) -> dict:
    secret = os.environ["CLAIMGUARD_JWT_SECRET"]
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise _unauthorized()
    if not payload.get("sub") or not payload.get("role"):
        raise _unauthorized()
    return {"username": payload["sub"], "role": payload["role"]}


def require_authenticated(user: dict = Depends(get_current_user)) -> dict:
    return user


def require_role(*roles: str):
    allowed = set(roles) | {"admin"}

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return checker