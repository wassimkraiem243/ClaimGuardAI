"""audit_events table

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("seq", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("ts", sa.Text, nullable=False),  # exact string that was hashed
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("claim_id", sa.Text, nullable=True),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
    )
    op.create_index("ix_audit_events_claim_id", "audit_events", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_claim_id", table_name="audit_events")
    op.drop_table("audit_events")