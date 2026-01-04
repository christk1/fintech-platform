from __future__ import annotations

import os
import sys
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from worker.application.processor import MessageProcessor
from worker.infrastructure.idempotency.in_memory import InMemoryIdempotencyStore


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def run_forever() -> None:
    region = os.getenv("AWS_REGION", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # LocalStack: http://localstack:4566
    queue_url = _required_env("SQS_PAYMENTS_QUEUE_URL")

    idempotency = InMemoryIdempotencyStore()
    processor = MessageProcessor(idempotency)

    session = boto3.Session()
    sqs = session.client("sqs", region_name=region, endpoint_url=endpoint_url)

    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=30,
            )
        except EndpointConnectionError:
            print(
                "LocalStack is not reachable yet. Ensure `localstack start` is running. Retrying...",
                file=sys.stderr,
            )
            time.sleep(2)
            continue
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"AWS.SimpleQueueService.NonExistentQueue", "QueueDoesNotExist"}:
                print(
                    "SQS queue does not exist yet. Run `make infra-local` to provision it. Retrying...",
                    file=sys.stderr,
                )
                time.sleep(2)
                continue
            raise

        messages = resp.get("Messages", [])
        if not messages:
            continue

        for msg in messages:
            message_id = msg.get("MessageId") or ""
            receipt = msg.get("ReceiptHandle") or ""
            body = msg.get("Body") or "{}"

            print(f"Received MessageId={message_id}")

            try:
                result = processor.process(message_id=message_id, body=body)
                if result.should_delete:
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                    print(f"Deleted MessageId={message_id}")
            except Exception:  # noqa: BLE001
                # In production: emit structured logs/metrics and rely on visibility timeout + DLQ.
                continue


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
