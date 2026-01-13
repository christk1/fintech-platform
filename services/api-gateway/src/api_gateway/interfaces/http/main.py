from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api_gateway.application.use_cases.publish_message import PublishMessage
from api_gateway.infrastructure.aws.sqs_message_publisher import SqsMessagePublisher
from api_gateway.infrastructure.cache.redis_client import build_redis_client
from api_gateway.infrastructure.persistence.db import get_engine
from api_gateway.interfaces.http.routers import v1, v2


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-redef]
        # Public API is snapshot-only: no direct balance aggregation calls.
        app.state.redis = build_redis_client()
        app.state.db_engine = get_engine()
        try:
            yield
        finally:
            try:
                await app.state.redis.aclose()
            except Exception:  # noqa: BLE001
                pass

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
