from typing import Protocol

from app.domain.normalized_claim import NormalizedClaim


class ClaimParser(Protocol):
    """Port: raw bytes -> normalized teaching envelopes."""

    def parse(self, raw: bytes) -> list[NormalizedClaim]: ...
