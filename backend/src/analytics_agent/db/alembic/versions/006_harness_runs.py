"""Persist bounded harness runs and their immutable evidence snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "harness_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", sa.Text(), nullable=False),
    )
    op.create_index("ix_harness_runs_conversation_id", "harness_runs", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_harness_runs_conversation_id", table_name="harness_runs")
    op.drop_table("harness_runs")
