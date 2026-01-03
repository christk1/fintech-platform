from __future__ import annotations

from typing import Protocol


class IdempotencyStore(Protocol):
    async def seen(self, key: str) -> bool: ...

    async def mark_seen(self, key: str, *, ttl_seconds: int) -> None: ...
