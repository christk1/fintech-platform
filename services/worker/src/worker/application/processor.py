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

    async def process(self, *, message_id: str, body: str) -> ProcessResult:
        # This is intentionally skeletal: boundary + idempotency pattern only.
        # Webhook handling / background jobs should be orchestrated from here.

        if await self._idempotency.seen(message_id):
            return ProcessResult(should_delete=True)

        _ = json.loads(body)  # validate/route by message type in real implementation

        await self._idempotency.mark_seen(message_id, ttl_seconds=24 * 60 * 60)
        return ProcessResult(should_delete=True)
