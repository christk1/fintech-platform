from __future__ import annotations

import json
from dataclasses import dataclass

from worker.domain.idempotency import IdempotencyStore


@dataclass(frozen=True)
class ProcessResult:
    should_delete: bool


class MessageProcessor:
    def __init__(self, idempotency: IdempotencyStore) -> None:
        self._idempotency = idempotency

    def process(self, *, message_id: str, body: str) -> ProcessResult:
        # This is intentionally skeletal: boundary + idempotency pattern only.
        # Webhook handling / background jobs should be orchestrated from here.

        ttl_seconds = 24 * 60 * 60
        if not self._idempotency.claim(message_id, ttl_seconds=ttl_seconds):
            return ProcessResult(should_delete=True)

        try:
            _ = json.loads(body)  # validate/route by message type in real implementation
            self._idempotency.complete(message_id, ttl_seconds=ttl_seconds)
            return ProcessResult(should_delete=True)
        except Exception:
            # Allow retries: don't permanently block the key on failed processing.
            self._idempotency.release(message_id)
            raise
