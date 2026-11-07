"""Persist batch evaluation summaries.

Revision ID: 007
Revises: 006
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "harness_batches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", sa.Text(), nullable=False),
    )
    op.create_index("ix_harness_batches_conversation_id", "harness_batches", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_harness_batches_conversation_id", table_name="harness_batches")
    op.drop_table("harness_batches")
