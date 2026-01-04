from __future__ import annotations

import json
import os
from typing import Any

from anyio import to_thread
import boto3

from api_gateway.application.ports.message_publisher import MessagePublisher


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


class SqsMessagePublisher(MessagePublisher):
    def __init__(self) -> None:
        self._region = os.getenv("AWS_REGION", "us-east-1")
        self._endpoint_url = os.getenv("AWS_ENDPOINT_URL")
        self._queue_url = _required_env("SQS_PAYMENTS_QUEUE_URL")

        session = boto3.Session()
        self._sqs = session.client(
            "sqs",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

    async def publish(self, *, message_type: str, payload: dict[str, Any]) -> None:
        body = json.dumps(
            {"type": message_type, "payload": payload},
            separators=(",", ":"),
        )

        def _send() -> None:
            self._sqs.send_message(
                QueueUrl=self._queue_url,
                MessageBody=body,
            )

        await to_thread.run_sync(_send)
