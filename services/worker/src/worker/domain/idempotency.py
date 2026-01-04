from __future__ import annotations

from typing import Protocol


class IdempotencyStore(Protocol):
    def claim(self, key: str, *, ttl_seconds: int) -> bool: ...

    def complete(self, key: str, *, ttl_seconds: int) -> None: ...

    def release(self, key: str) -> None: ...
