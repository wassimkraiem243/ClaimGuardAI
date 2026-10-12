import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@dataclass(frozen=True)
class Principal:
    actor: str
    role: str


def _reviewer_table() -> dict[str, Principal]:
    table: dict[str, Principal] = {}
    for item in filter(None, (x.strip() for x in settings.reviewer_keys.split(","))):
        key, actor, role = (item.split(":") + ["", ""])[:3]
        if key and actor and role in {"reviewer", "admin"}:
            table[key] = Principal(actor, role)
    return table


def require_reviewer(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> Principal:
    """Authenticated human identity. The audit 'actor' comes from here, never from the request body."""
    for key, principal in _reviewer_table().items():
        if x_api_key and hmac.compare_digest(x_api_key, key):
            return principal
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reviewer key required")
