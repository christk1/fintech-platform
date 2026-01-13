from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, func
from sqlalchemy import BigInteger

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


balance_snapshots = Table(
    "balance_snapshots",
    metadata,
    Column("client_id", String, primary_key=True),
    Column("generated_at_unix_ms", BigInteger, primary_key=True),
    Column("snapshot_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index("balance_snapshots_client_id_generated_at_idx", balance_snapshots.c.client_id, balance_snapshots.c.generated_at_unix_ms)
