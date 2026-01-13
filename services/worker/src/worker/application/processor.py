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

    def _handle_balance_reconcile(self, payload: object) -> None:
        # Placeholder for the real reconciliation workflow.
        # For now we accept the scheduled trigger and keep the worker healthy.
        return

    def process(self, *, message_id: str, body: str) -> ProcessResult:
        # This is intentionally skeletal: boundary + idempotency pattern only.
        # Webhook handling / background jobs should be orchestrated from here.

        ttl_seconds = 24 * 60 * 60
        if not self._idempotency.claim(message_id, ttl_seconds=ttl_seconds):
            return ProcessResult(should_delete=True)

        try:
            decoded = json.loads(body)
            if isinstance(decoded, dict):
                message_type = decoded.get("message_type")
                payload = decoded.get("payload")

                if message_type == "balance.reconcile":
                    self._handle_balance_reconcile(payload)

            self._idempotency.complete(message_id, ttl_seconds=ttl_seconds)
            return ProcessResult(should_delete=True)
        except Exception:
            # Allow retries: don't permanently block the key on failed processing.
            self._idempotency.release(message_id)
            raise
