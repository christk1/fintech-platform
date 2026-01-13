from __future__ import annotations

from contextvars import Token
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import metrics, trace
from opentelemetry.context import attach, detach
from opentelemetry.propagate import extract


class ReconcileTelemetry:
    def __init__(self) -> None:
        self._tracer = trace.get_tracer("worker.reconcile")
        self._meter = metrics.get_meter("worker.reconcile")

        self._reconcile_started = self._meter.create_counter(
            "worker_balance_reconcile_started_total",
            description="Number of balance reconcile attempts started by the worker",
        )
        self._reconcile_succeeded = self._meter.create_counter(
            "worker_balance_reconcile_succeeded_total",
            description="Number of balance reconciles completed successfully",
        )
        self._reconcile_failed = self._meter.create_counter(
            "worker_balance_reconcile_failed_total",
            description="Number of balance reconciles that failed",
        )

        self._reconcile_grpc_ms_hist = self._meter.create_histogram(
            "worker_balance_reconcile_grpc_ms",
            unit="ms",
            description="Latency of gRPC GetMetrics call (milliseconds)",
        )
        self._reconcile_db_ms_hist = self._meter.create_histogram(
            "worker_balance_reconcile_db_insert_ms",
            unit="ms",
            description="Latency of inserting snapshot into Postgres (milliseconds)",
        )
        self._reconcile_total_ms_hist = self._meter.create_histogram(
            "worker_balance_reconcile_total_ms",
            unit="ms",
            description="End-to-end reconciliation latency (milliseconds)",
        )

    def stage_attrs(self, *, trigger: str, reason: str) -> dict[str, str]:
        return {"trigger": trigger or "unknown", "reason": reason or "unknown"}

    def reconcile_started(self, attrs: dict[str, str]) -> None:
        self._reconcile_started.add(1, attrs)

    def reconcile_succeeded(self, attrs: dict[str, str]) -> None:
        self._reconcile_succeeded.add(1, attrs)

    def reconcile_failed(self, attrs: dict[str, str]) -> None:
        self._reconcile_failed.add(1, attrs)

    def record_grpc_ms(self, *, grpc_ms: int, attrs: dict[str, str]) -> None:
        self._reconcile_grpc_ms_hist.record(grpc_ms, attrs)

    def record_db_ms(self, *, db_ms: int, attrs: dict[str, str]) -> None:
        self._reconcile_db_ms_hist.record(db_ms, attrs)

    def record_total_ms(self, *, total_ms: int, attrs: dict[str, str]) -> None:
        self._reconcile_total_ms_hist.record(total_ms, attrs)

    @contextmanager
    def reconcile_span(self, *, client_id: str, trigger: str, reason: str) -> Iterator[None]:
        with self._tracer.start_as_current_span(
            "balance.reconcile",
            attributes={
                "client_id": client_id,
                "trigger": trigger,
                "reason": reason,
            },
        ):
            yield

    @contextmanager
    def message_process_span(self, *, message_id: str, message_type: str) -> Iterator[None]:
        with self._tracer.start_as_current_span(
            "worker.message.process",
            attributes={
                "message_id": message_id,
                "message_type": message_type,
            },
        ):
            yield

    @contextmanager
    def grpc_span(self) -> Iterator[None]:
        with self._tracer.start_as_current_span("balance.grpc.get_metrics"):
            yield

    @contextmanager
    def db_span(self) -> Iterator[None]:
        with self._tracer.start_as_current_span("balance.db.insert_snapshot"):
            yield

    @contextmanager
    def redis_span(self) -> Iterator[None]:
        with self._tracer.start_as_current_span("balance.redis.set_snapshot"):
            yield


telemetry = ReconcileTelemetry()


def maybe_attach_trace_context(payload: Any) -> Token[Any] | None:
    """If payload includes W3C trace context, attach it and return a token."""

    if not isinstance(payload, dict):
        return None

    if not (payload.get("traceparent") or payload.get("tracestate")):
        return None

    carrier: dict[str, str] = {}
    if payload.get("traceparent"):
        carrier["traceparent"] = str(payload.get("traceparent"))
    if payload.get("tracestate"):
        carrier["tracestate"] = str(payload.get("tracestate"))

    ctx = extract(carrier)
    return attach(ctx)


def detach_trace_context(token: Token[Any] | None) -> None:
    if token is None:
        return
    detach(token)
