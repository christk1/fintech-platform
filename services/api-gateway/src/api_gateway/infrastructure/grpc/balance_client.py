from __future__ import annotations

import asyncio
import os

import grpc

from api_gateway.infrastructure.grpc import balance_pb2, balance_pb2_grpc


class BalanceGrpcClient:
    def __init__(self, target: str, *, channels: int) -> None:
        self._target = target
        self._channels = max(1, channels)
        self._channel_pool: list[grpc.aio.Channel] = []
        self._stub_pool: list[balance_pb2_grpc.BalanceServiceStub] = []
        self._rr = 0
        self._rr_lock = asyncio.Lock()

    @classmethod
    def from_env(cls) -> "BalanceGrpcClient":
        target = os.getenv("BALANCE_SERVICE_GRPC_TARGET", "balance-service:50051")
        channels = int(os.getenv("BALANCE_SERVICE_GRPC_CHANNELS", "3"))
        return cls(target=target, channels=channels)

    async def start(self) -> None:
        if self._stub_pool:
            return

        self._channel_pool = [
            grpc.aio.insecure_channel(self._target) for _ in range(self._channels)
        ]
        self._stub_pool = [
            balance_pb2_grpc.BalanceServiceStub(ch) for ch in self._channel_pool
        ]

        await asyncio.gather(*(ch.channel_ready() for ch in self._channel_pool))

    async def stop(self) -> None:
        channels = self._channel_pool
        self._channel_pool = []
        self._stub_pool = []
        if channels:
            await asyncio.gather(*(ch.close() for ch in channels), return_exceptions=True)

    async def _stub(self) -> balance_pb2_grpc.BalanceServiceStub:
        if not self._stub_pool:
            raise RuntimeError("BalanceGrpcClient not started")

        async with self._rr_lock:
            idx = self._rr % len(self._stub_pool)
            self._rr += 1
            return self._stub_pool[idx]

    async def ping(self) -> str:
        stub = await self._stub()
        response = await stub.Ping(balance_pb2.PingRequest())
        return response.status

    async def get_metrics(
        self, *, client_id: str, provider_ids: list[str] | None = None
    ) -> list[balance_pb2.ProviderMetric]:
        stub = await self._stub()
        request = balance_pb2.MetricsRequest(
            provider_ids=provider_ids or [],
            client_id=client_id,
        )
        response = await stub.GetMetrics(request)

        return list(response.metrics)
