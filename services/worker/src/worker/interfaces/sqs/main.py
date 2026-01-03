from __future__ import annotations

import asyncio
import os

import aioboto3

from worker.application.processor import MessageProcessor
from worker.infrastructure.idempotency.in_memory import InMemoryIdempotencyStore


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


async def run_forever() -> None:
    region = os.getenv("AWS_REGION", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # LocalStack: http://localstack:4566
    queue_url = _required_env("SQS_QUEUE_URL")

    idempotency = InMemoryIdempotencyStore()
    processor = MessageProcessor(idempotency)

    session = aioboto3.Session()
    async with session.client("sqs", region_name=region, endpoint_url=endpoint_url) as sqs:
        while True:
            resp = await sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=30,
            )

            messages = resp.get("Messages", [])
            if not messages:
                continue

            for msg in messages:
                message_id = msg.get("MessageId") or ""
                receipt = msg.get("ReceiptHandle") or ""
                body = msg.get("Body") or "{}"

                try:
                    result = await processor.process(message_id=message_id, body=body)
                    if result.should_delete:
                        await sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                except Exception:  # noqa: BLE001
                    # In production: emit structured logs/metrics and rely on visibility timeout + DLQ.
                    continue


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
