from __future__ import annotations

from typing import Any

from api_gateway.application.ports.message_publisher import MessagePublisher


class PublishMessage:
    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def execute(self, *, message_type: str, payload: dict[str, Any]) -> None:
        if not message_type:
            raise ValueError("message_type is required")
        await self._publisher.publish(message_type=message_type, payload=payload)
