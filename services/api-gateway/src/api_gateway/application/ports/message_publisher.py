from __future__ import annotations

from typing import Any, Protocol


class MessagePublisher(Protocol):
    async def publish(self, *, message_type: str, payload: dict[str, Any]) -> None: ...
