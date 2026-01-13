"""create balance_snapshots

Revision ID: 002_create_balance_snapshots
Revises: 001_create_processed_events
Create Date: 2026-01-13

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "002_create_balance_snapshots"
down_revision = "001_create_processed_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "balance_snapshots",
        sa.Column("client_id", sa.String(), primary_key=True),
        sa.Column("generated_at_unix_ms", sa.BigInteger(), primary_key=True),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "balance_snapshots_client_id_generated_at_idx",
        "balance_snapshots",
        ["client_id", "generated_at_unix_ms"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("balance_snapshots_client_id_generated_at_idx", table_name="balance_snapshots")
    op.drop_table("balance_snapshots")
