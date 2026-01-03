from __future__ import annotations

import json
import os
from typing import Any

import aioboto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


class PublishRequest(BaseModel):
    message_type: str = Field(min_length=1)
    payload: dict[str, Any]


def create_app() -> FastAPI:
    app = FastAPI(title="api-gateway")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/messages")
    async def publish_message(body: PublishRequest) -> dict[str, str]:
        # NOTE: Auth/orchestration/validation live here; business logic is intentionally absent.
        # This endpoint only publishes to SQS. It does NOT create any infrastructure.

        region = os.getenv("AWS_REGION", "us-east-1")
        endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # LocalStack: http://localstack:4566
        queue_url = _required_env("SQS_QUEUE_URL")

        session = aioboto3.Session()
        async with session.client("sqs", region_name=region, endpoint_url=endpoint_url) as sqs:
            try:
                await sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(
                        {"type": body.message_type, "payload": body.payload}, separators=(",", ":")
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail="Failed to publish message") from exc

        return {"status": "queued"}

    return app


app = create_app()


def main() -> None:
    raise SystemExit(
        "Run via: fastapi run --host 0.0.0.0 --port 8000 api_gateway.interfaces.http.main:app"
    )
