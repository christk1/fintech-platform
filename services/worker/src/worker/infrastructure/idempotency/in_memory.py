from __future__ import annotations

import time

from worker.domain.idempotency import IdempotencyStore


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._expiry_by_key: dict[str, float] = {}

    def claim(self, key: str, *, ttl_seconds: int) -> bool:
        now = time.time()
        expiry = self._expiry_by_key.get(key)
        if expiry is not None and expiry > now:
            return False
        self._expiry_by_key[key] = now + ttl_seconds
        return True

    def complete(self, key: str, *, ttl_seconds: int) -> None:
        self._expiry_by_key[key] = time.time() + ttl_seconds

    def release(self, key: str) -> None:
        self._expiry_by_key.pop(key, None)
