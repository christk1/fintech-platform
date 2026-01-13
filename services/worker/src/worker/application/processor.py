from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass

import grpc
from sqlalchemy import create_engine, text

from worker.domain.idempotency import IdempotencyStore
from worker.infrastructure.cache.redis_client import build_redis_client
from worker.infrastructure.grpc.balance_client import BalanceGrpcClient
from worker.infrastructure.observability.reconcile_telemetry import (
    detach_trace_context,
    maybe_attach_trace_context,
    telemetry,
)


logger = logging.getLogger(__name__)


def _normalize_database_url(database_url: str) -> str:
    # Prefer psycopg (C-accelerated) in the worker for lower latency.
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql+pg8000://"):
        return database_url.replace("postgresql+pg8000://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


@dataclass(frozen=True)
class ProcessResult:
    should_delete: bool


class MessageProcessor:
    def __init__(self, idempotency: IdempotencyStore) -> None:
        self._idempotency = idempotency
        # Keep a long-lived channel to avoid per-message connection churn.
        self._balance_client = BalanceGrpcClient.from_env()
        self._balance_client.start()

        # Keep a pooled DB engine to avoid per-message connect handshakes.
        database_url = _normalize_database_url(os.environ["DATABASE_URL"])
        self._db_engine = create_engine(
            database_url,
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "0") == "1",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        )

        self._insert_snapshot_stmt = text(
            """
            INSERT INTO balance_snapshots (client_id, generated_at_unix_ms, snapshot_json)
            VALUES (:client_id, :generated_at_unix_ms, CAST(:snapshot_json AS jsonb))
            """
        )

    def _fetch_metrics(self, *, client_id: str, trigger: str, reason: str) -> tuple[list[dict], int]:
        with telemetry.grpc_span():
            started = time.perf_counter()
            proto_metrics = self._balance_client.get_metrics(client_id=client_id)
            grpc_ms = int((time.perf_counter() - started) * 1000)

        telemetry.record_grpc_ms(
            grpc_ms=grpc_ms,
            attrs=telemetry.stage_attrs(trigger=trigger, reason=reason),
        )

        metrics_list = [
            {
                "provider_id": m.provider_id,
                "provider_name": m.provider_name,
                "provider_type": m.provider_type,
                "currency": m.currency,
                "available_cents": int(m.available_cents),
                "ledger_cents": int(m.ledger_cents),
                "as_of_unix_ms": int(m.as_of_unix_ms),
            }
            for m in proto_metrics
        ]

        return metrics_list, grpc_ms

    def _insert_snapshot(self, *, snapshot: dict, trigger: str, reason: str) -> int:
        with telemetry.db_span():
            started = time.perf_counter()
            with self._db_engine.begin() as conn:
                conn.execute(
                    self._insert_snapshot_stmt,
                    {
                        "client_id": snapshot["client_id"],
                        "generated_at_unix_ms": snapshot["generated_at_unix_ms"],
                        "snapshot_json": json.dumps(snapshot),
                    },
                )
            db_ms = int((time.perf_counter() - started) * 1000)

        telemetry.record_db_ms(
            db_ms=db_ms,
            attrs=telemetry.stage_attrs(trigger=trigger, reason=reason),
        )
        return db_ms

    def _cache_snapshot(self, *, snapshot: dict) -> int:
        redis = build_redis_client()

        async def _cache() -> None:
            try:
                await redis.set(
                    f"balance:snapshot:{snapshot['client_id']}",
                    json.dumps(snapshot),
                    ex=3600,
                )
            finally:
                await redis.aclose()

        with telemetry.redis_span():
            started = time.perf_counter()
            asyncio.run(_cache())
            return int((time.perf_counter() - started) * 1000)

    def _handle_balance_reconcile(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return

        client_id = payload.get("client_id")
        if not client_id:
            return

        trigger = str(payload.get("trigger") or "")
        reason = str(payload.get("reason") or "")

        stage_attrs = telemetry.stage_attrs(trigger=trigger, reason=reason)
        telemetry.reconcile_started(stage_attrs)

        started_at = time.perf_counter()
        logger.info("balance.reconcile start client_id=%s", client_id)

        with telemetry.reconcile_span(client_id=str(client_id), trigger=trigger, reason=reason):
            try:
                metrics_list, grpc_ms = self._fetch_metrics(
                    client_id=str(client_id),
                    trigger=trigger,
                    reason=reason,
                )

                snapshot = {
                    "client_id": str(client_id),
                    "generated_at_unix_ms": int(time.time() * 1000),
                    "metrics": metrics_list,
                }

                db_ms = self._insert_snapshot(snapshot=snapshot, trigger=trigger, reason=reason)
                redis_ms = self._cache_snapshot(snapshot=snapshot)

                total_ms = int((time.perf_counter() - started_at) * 1000)
                telemetry.record_total_ms(total_ms=total_ms, attrs=stage_attrs)
                logger.info(
                    "balance.reconcile done client_id=%s metrics=%d grpc_ms=%d db_ms=%d redis_ms=%d total_ms=%d",
                    snapshot["client_id"],
                    len(metrics_list),
                    grpc_ms,
                    db_ms,
                    redis_ms,
                    total_ms,
                )
                telemetry.reconcile_succeeded(stage_attrs)
            except Exception:
                telemetry.reconcile_failed(stage_attrs)
                raise

    def process(self, *, message_id: str, body: str) -> ProcessResult:
        decoded = None
        try:
            decoded = json.loads(body or "{}")
        except Exception:
            decoded = None

        message_type = decoded.get("message_type") if isinstance(decoded, dict) else None
        payload = decoded.get("payload") if isinstance(decoded, dict) else None

        token = maybe_attach_trace_context(payload)

        ttl_seconds = 24 * 60 * 60
        idempotency_key = message_id

        # EventBridge/SQS is at-least-once and LocalStack can deliver duplicates.
        # For scheduled reconciles, dedupe per minute per client.
        if (
            message_type == "balance.reconcile"
            and isinstance(payload, dict)
            and payload.get("trigger") == "eventbridge"
            and payload.get("reason") == "scheduled"
            and payload.get("client_id")
        ):
            minute_bucket = int(time.time() // 60)
            idempotency_key = f"balance.reconcile:scheduled:{payload['client_id']}:{minute_bucket}"
            ttl_seconds = 2 * 60

        try:
            with telemetry.message_process_span(
                message_id=message_id,
                message_type=str(message_type or ""),
            ):
                if not self._idempotency.claim(idempotency_key, ttl_seconds=ttl_seconds):
                    logger.info(
                        "skip duplicate idempotency_key=%s message_id=%s",
                        idempotency_key,
                        message_id,
                    )
                    return ProcessResult(should_delete=True)

                try:
                    if message_type == "balance.reconcile":
                        self._handle_balance_reconcile(payload)
                    else:
                        logger.info(
                            "ignored message_type=%s message_id=%s", message_type, message_id
                        )

                    self._idempotency.complete(idempotency_key, ttl_seconds=ttl_seconds)
                    return ProcessResult(should_delete=True)
                except grpc.RpcError as exc:
                    # Transient network churn / peer cancellations are expected in local docker.
                    # Do not delete the message; release idempotency key to allow retry.
                    code = exc.code() if hasattr(exc, "code") else None
                    details = exc.details() if hasattr(exc, "details") else str(exc)
                    logger.warning(
                        "message processing transient grpc error message_id=%s code=%s details=%s",
                        message_id,
                        code,
                        details,
                    )
                    self._idempotency.release(idempotency_key)
                    return ProcessResult(should_delete=False)
                except Exception:
                    logger.exception("message processing failed message_id=%s", message_id)
                    self._idempotency.release(idempotency_key)
                    raise
        finally:
            detach_trace_context(token)
