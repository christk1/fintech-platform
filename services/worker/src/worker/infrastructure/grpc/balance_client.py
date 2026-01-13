from __future__ import annotations

import os
import time

import grpc

from worker.infrastructure.grpc import balance_pb2, balance_pb2_grpc


class BalanceGrpcClient:
    """Synchronous gRPC client.

    The worker is a synchronous process (boto3 polling loop). Using `grpc.aio` inside
    `asyncio.run()` per message can lead to surprising `CANCELLED` errors due to event
    loop/channel lifecycle interactions. A sync client is simpler and more robust here.
    """

    def __init__(self, target: str) -> None:
        self._target = target
        self._channel: grpc.Channel | None = None
        self._stub: balance_pb2_grpc.BalanceServiceStub | None = None

    @classmethod
    def from_env(cls) -> "BalanceGrpcClient":
        target = os.getenv("BALANCE_SERVICE_GRPC_TARGET", "balance-service:50051")
        return cls(target=target)

    def start(self) -> None:
        if self._stub is not None:
            return
        self._channel = grpc.insecure_channel(self._target)
        self._stub = balance_pb2_grpc.BalanceServiceStub(self._channel)

    def stop(self) -> None:
        ch = self._channel
        self._channel = None
        self._stub = None
        if ch is not None:
            ch.close()

    def __enter__(self) -> "BalanceGrpcClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.stop()

    def _get_stub(self) -> balance_pb2_grpc.BalanceServiceStub:
        if self._stub is None:
            raise RuntimeError("BalanceGrpcClient not started")
        return self._stub

    def get_metrics(
        self, *, client_id: str, provider_ids: list[str] | None = None
    ) -> list[balance_pb2.ProviderMetric]:
        stub = self._get_stub()
        request = balance_pb2.MetricsRequest(provider_ids=provider_ids or [], client_id=client_id)

        timeout_s = float(os.getenv("BALANCE_SERVICE_GRPC_TIMEOUT_SECONDS", "5"))
        max_attempts = int(os.getenv("BALANCE_SERVICE_GRPC_MAX_ATTEMPTS", "5"))
        if max_attempts < 1:
            max_attempts = 1

        last_exc: grpc.RpcError | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = stub.GetMetrics(
                    request,
                    timeout=timeout_s,
                    wait_for_ready=True,
                )
                return list(response.metrics)
            except grpc.RpcError as exc:
                last_exc = exc
                code = exc.code() if hasattr(exc, "code") else None

                # Retry transient errors (startup races / connection churn).
                if code in {
                    grpc.StatusCode.CANCELLED,
                    grpc.StatusCode.UNAVAILABLE,
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                } and attempt < max_attempts:
                    time.sleep(min(0.5, 0.1 * (2 ** (attempt - 1))))
                    continue
                raise

        assert last_exc is not None
        raise last_exc
