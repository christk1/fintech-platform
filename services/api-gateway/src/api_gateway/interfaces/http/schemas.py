from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PublishRequest(BaseModel):
    message_type: str = Field(min_length=1)
    payload: dict[str, Any]


class PublishResponse(BaseModel):
    status: str
