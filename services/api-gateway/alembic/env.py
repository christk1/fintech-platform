from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context

from api_gateway.infrastructure.persistence.db import get_engine, normalize_database_url
from api_gateway.infrastructure.persistence.models import metadata

# Alembic Config object.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = metadata


def run_migrations_offline() -> None:
    url = normalize_database_url(os.environ["DATABASE_URL"])
    config.set_main_option("sqlalchemy.url", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
