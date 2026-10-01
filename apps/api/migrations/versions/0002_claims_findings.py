"""claims, claim_lines, findings

Revision ID: 0002
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("claim_id", sa.Text, primary_key=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("patient_id", sa.Text, nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("received_at", sa.Text, nullable=False),
        sa.Column("package", JSONB, nullable=False),
    )
    op.create_index("ix_claims_patient_id", "claims", ["patient_id"])
    op.create_table(
        "claim_lines",
        sa.Column("claim_id", sa.Text, sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer, nullable=False),
        sa.Column("procedure_code", sa.Text, nullable=False),
        sa.Column("service_date", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("claim_id", "line_no"),
    )
    op.create_index("ix_claim_lines_service", "claim_lines", ["procedure_code", "service_date"])
    op.create_table(
        "findings",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("claim_id", sa.Text, sa.ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("line_no", sa.Integer, nullable=True),
        sa.Column("data", JSONB, nullable=False),
    )
    op.create_index("ix_findings_claim_id", "findings", ["claim_id"])


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("claim_lines")
    op.drop_table("claims")