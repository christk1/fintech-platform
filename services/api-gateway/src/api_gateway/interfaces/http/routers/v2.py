from __future__ import annotations

import asyncio
import json
import logging
import time
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from opentelemetry.propagate import inject

from api_gateway.interfaces.http.schemas import (
    BalanceMetricsResponse,
    BalancePingResponse,
    ProviderMetric,
    PublishRequest,
    PublishResponse,
)


router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/messages", response_model=PublishResponse)
async def publish_message_v2(body: PublishRequest, request: Request) -> PublishResponse:
    # v2 initially matches v1 for zero breaking changes.
    publish_message = getattr(request.app.state, "publish_message_use_case", None)
    if publish_message is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    try:
        await publish_message.execute(message_type=body.message_type, payload=body.payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Failed to publish message") from exc

    return PublishResponse(status="queued")


@router.get("/balance/ping", response_model=BalancePingResponse)
async def balance_ping(request: Request) -> BalancePingResponse:
    redis = getattr(request.app.state, "redis", None)
    engine = getattr(request.app.state, "db_engine", None)
    if redis is None or engine is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    try:
        await redis.ping()

        def _db_ping() -> None:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        await asyncio.to_thread(_db_ping)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Snapshot storage unavailable") from exc

    return BalancePingResponse(status="ok")


@router.get("/balance/metrics", response_model=BalanceMetricsResponse)
async def balance_metrics(request: Request, client_id: str) -> BalanceMetricsResponse:
    redis = getattr(request.app.state, "redis", None)
    engine = getattr(request.app.state, "db_engine", None)
    if redis is None or engine is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    stale_after_seconds = int(
        getattr(request.app.state, "balance_snapshot_stale_after_seconds", 300)
    )
    redis_key = f"balance:snapshot:{client_id}"

    snapshot: dict | None = None

    raw = await redis.get(redis_key)
    if raw:
        try:
            snapshot = json.loads(raw)
        except Exception:
            snapshot = None

    if snapshot is None:
        def _load_latest_from_db() -> dict | None:
            query = text(
                """
                SELECT snapshot_json
                FROM balance_snapshots
                WHERE client_id = :client_id
                ORDER BY generated_at_unix_ms DESC
                LIMIT 1
                """
            )
            with engine.connect() as conn:
                row = conn.execute(query, {"client_id": client_id}).mappings().first()
            if not row:
                return None

            value = row["snapshot_json"]
            if isinstance(value, dict):
                return value
            if isinstance(value, str) and value:
                return json.loads(value)
            # Fallback for DB drivers returning custom mapping objects.
            try:
                return dict(value)
            except Exception:
                return None

        snapshot = await asyncio.to_thread(_load_latest_from_db)
        if snapshot is not None:
            # Cache best-effort (don't fail request on cache write).
            try:
                await redis.set(redis_key, json.dumps(snapshot), ex=3600)
            except Exception:
                pass

    def _is_stale(snap: dict | None) -> bool:
        if not snap:
            return True
        gen_ms = int(snap.get("generated_at_unix_ms") or 0)
        if gen_ms <= 0:
            return True
        now_ms = int(time.time() * 1000)
        return (now_ms - gen_ms) > (stale_after_seconds * 1000)

    if _is_stale(snapshot):
        # Optionally enqueue a refresh request, but never block on aggregation.
        publish_message = getattr(request.app.state, "publish_message_use_case", None)
        if publish_message is not None:
            try:
                logger.info("enqueue balance.reconcile client_id=%s reason=stale_or_missing", client_id)

                carrier: dict[str, str] = {}
                inject(carrier)
                await publish_message.execute(
                    message_type="balance.reconcile",
                    payload={
                        "client_id": client_id,
                        "trigger": "api_read",
                        "reason": "stale_or_missing",
                        **carrier,
                    },
                )
            except Exception:
                pass

    metrics_raw = (snapshot or {}).get("metrics") or []
    metrics = [ProviderMetric(**m) for m in metrics_raw]

    return BalanceMetricsResponse(metrics=metrics)
