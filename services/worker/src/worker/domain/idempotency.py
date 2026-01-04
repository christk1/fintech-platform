from __future__ import annotations

from typing import Protocol


class IdempotencyStore(Protocol):
    def seen(self, key: str) -> bool: ...

    def mark_seen(self, key: str, *, ttl_seconds: int) -> None: ...
