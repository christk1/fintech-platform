from __future__ import annotations

import json
import os
from typing import Any

import aioboto3

from api_gateway.application.ports.message_publisher import MessagePublisher


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


class SqsMessagePublisher(MessagePublisher):
    async def publish(self, *, message_type: str, payload: dict[str, Any]) -> None:
        region = os.getenv("AWS_REGION", "us-east-1")
        endpoint_url = os.getenv("AWS_ENDPOINT_URL")
        queue_url = _required_env("SQS_PAYMENTS_QUEUE_URL")

        session = aioboto3.Session()
        async with session.client(  # pyright: ignore[reportGeneralTypeIssues]
            "sqs", region_name=region, endpoint_url=endpoint_url
        ) as sqs:
            await sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(
                    {"type": message_type, "payload": payload}, separators=(",", ":")
                ),
            )
