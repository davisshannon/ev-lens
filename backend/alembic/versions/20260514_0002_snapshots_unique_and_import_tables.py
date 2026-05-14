"""Add unique constraint to vehicle_snapshots (vehicle_id, observed_at)

Required so that the TeslaMate import service can use ON CONFLICT DO NOTHING
for idempotent snapshot upserts.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the non-unique index and re-create it as unique.
    op.drop_index("ix_snapshots_vehicle_observed", table_name="vehicle_snapshots")
    op.create_index(
        "ix_snapshots_vehicle_observed",
        "vehicle_snapshots",
        ["vehicle_id", "observed_at"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_vehicle_observed", table_name="vehicle_snapshots")
    op.create_index(
        "ix_snapshots_vehicle_observed",
        "vehicle_snapshots",
        ["vehicle_id", "observed_at"],
        unique=False,
    )
