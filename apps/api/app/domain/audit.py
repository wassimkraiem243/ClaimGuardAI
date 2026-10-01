from typing import Optional, Protocol
from fastapi import APIRouter
from pydantic import BaseModel

router=APIRouter()

class AuditEvent(BaseModel):
    seq: int
    ts: str
    type: str
    claim_id: Optional[str]
    details: dict
    prev_hash: str
    hash: str


class AuditLog(Protocol):
    """Port: append-only log of checks, findings and decisions."""

    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent: ...
    def read(self, claim_id: Optional[str] = None) -> list[AuditEvent]: ...
    def verify(self) -> tuple[bool, Optional[int]]: ...