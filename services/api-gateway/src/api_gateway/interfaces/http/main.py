from __future__ import annotations

from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from api_gateway.application.use_cases.publish_message import PublishMessage
from api_gateway.infrastructure.aws.sqs_message_publisher import SqsMessagePublisher
from api_gateway.infrastructure.grpc.balance_client import BalanceGrpcClient
from api_gateway.interfaces.http.routers import v1, v2


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-redef]
        client = BalanceGrpcClient.from_env()
        await client.start()
        app.state.balance_grpc_client = client
        try:
            yield
        finally:
            with suppress(Exception):  # noqa: BLE001
                await client.stop()

    app = FastAPI(title="api-gateway", lifespan=lifespan)

    # Dependency wiring (outer layers depend inward).
    app.state.publish_message_use_case = PublishMessage(publisher=SqsMessagePublisher())

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(v1.router, prefix="/v1", tags=["v1"])
    app.include_router(v2.router, prefix="/v2", tags=["v2"])

    return app


app = create_app()


def main() -> None:
    raise SystemExit(
        "Run via: fastapi run --host 0.0.0.0 --port 8000 api_gateway.interfaces.http.main:app"
    )
