"""create processed_events

Revision ID: 001_create_processed_events
Revises: 
Create Date: 2026-01-04

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_create_processed_events"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "processed_events_expires_at_idx",
        "processed_events",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("processed_events_expires_at_idx", table_name="processed_events")
    op.drop_table("processed_events")
