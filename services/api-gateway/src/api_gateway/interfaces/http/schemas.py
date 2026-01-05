from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PublishRequest(BaseModel):
    message_type: str = Field(min_length=1)
    payload: dict[str, Any]


class PublishResponse(BaseModel):
    status: str


class BalancePingResponse(BaseModel):
    status: str


class ProviderMetric(BaseModel):
    provider_id: str
    provider_name: str
    provider_type: str
    currency: str
    available_cents: int
    ledger_cents: int
    as_of_unix_ms: int


class BalanceMetricsResponse(BaseModel):
    metrics: list[ProviderMetric]
