from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def normalize_database_url(database_url: str) -> str:
    # Our env var uses `postgresql://...`.
    # SQLAlchemy needs an explicit DBAPI driver when psycopg isn't installed.
    if database_url.startswith("postgresql+pg8000://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+pg8000://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+pg8000://", 1)
    return database_url


def get_engine(database_url: str | None = None) -> Engine:
    url = normalize_database_url(database_url or os.environ["DATABASE_URL"])
    return create_engine(url, pool_pre_ping=True)
