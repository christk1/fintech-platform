from __future__ import annotations

import os

import grpc

from api_gateway.infrastructure.grpc import balance_pb2, balance_pb2_grpc


class BalanceGrpcClient:
    def __init__(self, target: str) -> None:
        self._target = target
        self._channel: grpc.aio.Channel | None = None
        self._stub: balance_pb2_grpc.BalanceServiceStub | None = None

    @classmethod
    def from_env(cls) -> "BalanceGrpcClient":
        target = os.getenv("BALANCE_SERVICE_GRPC_TARGET", "balance-service:50051")
        return cls(target=target)

    async def start(self) -> None:
        self._channel = grpc.aio.insecure_channel(self._target)
        self._stub = balance_pb2_grpc.BalanceServiceStub(self._channel)
        await self._channel.channel_ready()

    async def stop(self) -> None:
        if self._channel is not None:
            await self._channel.close()

    async def ping(self) -> str:
        if self._stub is None:
            raise RuntimeError("BalanceGrpcClient not started")

        response = await self._stub.Ping(balance_pb2.PingRequest())
        return response.status

    async def get_metrics(
        self, *, client_id: str, provider_ids: list[str] | None = None
    ) -> list[balance_pb2.ProviderMetric]:
        if self._stub is None:
            raise RuntimeError("BalanceGrpcClient not started")

        request = balance_pb2.MetricsRequest(
            provider_ids=provider_ids or [],
            client_id=client_id,
        )
        response = await self._stub.GetMetrics(request)

        return list(response.metrics)
