from __future__ import annotations

import time

from worker.domain.idempotency import IdempotencyStore


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._expiry_by_key: dict[str, float] = {}

    def seen(self, key: str) -> bool:
        now = time.time()
        expiry = self._expiry_by_key.get(key)
        if expiry is None:
            return False
        if expiry <= now:
            self._expiry_by_key.pop(key, None)
            return False
        return True

    def mark_seen(self, key: str, *, ttl_seconds: int) -> None:
        self._expiry_by_key[key] = time.time() + ttl_seconds
