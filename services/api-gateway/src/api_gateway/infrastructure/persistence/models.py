from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, func

metadata = MetaData()

processed_events = Table(
    "processed_events",
    metadata,
    Column("key", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index("processed_events_expires_at_idx", processed_events.c.expires_at)
