from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from worker.domain.idempotency import IdempotencyStore


@dataclass
class PostgresIdempotencyStore(IdempotencyStore):
    database_url: str
    table_name: str = "processed_events"

    _engine_cached: Engine | None = field(default=None, init=False, repr=False)

    _STATUS_PROCESSING: Final[str] = "processing"
    _STATUS_COMPLETED: Final[str] = "completed"

    def _normalized_database_url(self) -> str:
        # Our env var uses `postgresql://...`.
        # SQLAlchemy needs an explicit DBAPI driver when psycopg isn't installed.
        if self.database_url.startswith("postgresql+pg8000://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+pg8000://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+pg8000://", 1)
        return self.database_url

    def _validate_table_name(self) -> None:
        # Avoid SQL injection via env-configured table name.
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.table_name):
            raise ValueError(f"Invalid table name: {self.table_name!r}")

    def _engine(self) -> Engine:
        self._validate_table_name()
        if self._engine_cached is None:
            self._engine_cached = create_engine(self._normalized_database_url(), pool_pre_ping=True)
        return self._engine_cached

    def assert_schema_ready(self) -> None:
        # Migrations live in api-gateway; worker should only wait for them.
        query = text(f"SELECT 1 FROM {self.table_name} LIMIT 1")
        engine = self._engine()
        with engine.connect() as conn:
            conn.execute(query)

    def claim(self, key: str, *, ttl_seconds: int) -> bool:
        """Attempt to claim processing rights for this key.

        Returns True only for the first consumer (or after expiry).
        Others should treat it as a duplicate and delete the message.
        """
        query = text(
            f"""
            INSERT INTO {self.table_name} (key, status, expires_at)
            VALUES (:key, :status, now() + (:ttl_seconds * interval '1 second'))
            ON CONFLICT (key) DO UPDATE
            SET
              status = EXCLUDED.status,
              expires_at = EXCLUDED.expires_at,
              updated_at = now()
            WHERE {self.table_name}.expires_at < now()
            RETURNING key;
            """
        )

        engine = self._engine()
        with engine.begin() as conn:
            result = conn.execute(
                query,
                {"key": key, "status": self._STATUS_PROCESSING, "ttl_seconds": ttl_seconds},
            )
            row = result.first()

        return row is not None

    def complete(self, key: str, *, ttl_seconds: int) -> None:
        query = text(
            f"""
            UPDATE {self.table_name}
            SET status = :status,
                expires_at = now() + (:ttl_seconds * interval '1 second'),
                updated_at = now()
            WHERE key = :key;
            """
        )

        engine = self._engine()
        with engine.begin() as conn:
            conn.execute(
                query,
                {"status": self._STATUS_COMPLETED, "ttl_seconds": ttl_seconds, "key": key},
            )

    def release(self, key: str) -> None:
        """Release a processing claim so the message can be retried.

        If the worker crashes without releasing, expiry will eventually allow reclaim.
        """
        query = text(
            f"""
            DELETE FROM {self.table_name}
            WHERE key = :key AND status = :status;
            """
        )

        engine = self._engine()
        with engine.begin() as conn:
            conn.execute(query, {"key": key, "status": self._STATUS_PROCESSING})


def idempotency_table_name_from_env() -> str:
    return os.getenv("IDEMPOTENCY_TABLE", "processed_events")
