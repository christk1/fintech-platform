from __future__ import annotations

import grpc
from fastapi import APIRouter, HTTPException, Request

from api_gateway.infrastructure.grpc.balance_client import BalanceGrpcClient
from api_gateway.interfaces.http.schemas import (
    BalanceMetricsResponse,
    BalancePingResponse,
    ProviderMetric,
    PublishRequest,
    PublishResponse,
)


router = APIRouter()


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
    client: BalanceGrpcClient | None = getattr(request.app.state, "balance_grpc_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    try:
        status = await client.ping()
    except grpc.aio.AioRpcError as exc:
        raise HTTPException(status_code=502, detail="Balance service unavailable") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Balance service unavailable") from exc

    return BalancePingResponse(status=status)


@router.get("/balance/metrics", response_model=BalanceMetricsResponse)
async def balance_metrics(request: Request, client_id: str) -> BalanceMetricsResponse:
    client: BalanceGrpcClient | None = getattr(request.app.state, "balance_grpc_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    try:
        proto_metrics = await client.get_metrics(client_id=client_id)
    except grpc.aio.AioRpcError as exc:
        raise HTTPException(status_code=502, detail="Balance service unavailable") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Balance service unavailable") from exc

    metrics = [
        ProviderMetric(
            provider_id=m.provider_id,
            provider_name=m.provider_name,
            provider_type=m.provider_type,
            currency=m.currency,
            available_cents=int(m.available_cents),
            ledger_cents=int(m.ledger_cents),
            as_of_unix_ms=int(m.as_of_unix_ms),
        )
        for m in proto_metrics
    ]

    return BalanceMetricsResponse(metrics=metrics)
