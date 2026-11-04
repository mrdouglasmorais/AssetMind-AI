"""Application tables. Agno runtime tables are provisioned by Agno, not this migration."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_application_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyses_correlation_id", "analyses", ["correlation_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_table(
        "analysis_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_events_analysis_id", "analysis_events", ["analysis_id"])
    op.create_table(
        "usage_records",
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id"), primary_key=True),
        sa.Column("provider_calls", sa.Integer(), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_output_tokens", sa.Integer(), nullable=False),
        sa.Column("actual_input_tokens", sa.Integer(), nullable=True),
        sa.Column("actual_output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.String(length=32), nullable=False),
        sa.Column("actual_cost_usd", sa.String(length=32), nullable=True),
    )
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("period", sa.String(length=64), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_evidence_records_analysis_id", "evidence_records", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("evidence_records")
    op.drop_table("usage_records")
    op.drop_table("analysis_events")
    op.drop_table("analyses")
