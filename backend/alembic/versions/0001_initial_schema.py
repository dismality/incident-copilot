"""Initial incident, evidence, action, approval, and audit tables."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("scenario_key", sa.String(80), nullable=False),
        sa.Column("service", sa.String(120), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("alert_summary", sa.Text, nullable=False),
        sa.Column("alert_data", sa.JSON, nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("likely_cause", sa.Text),
        sa.Column("confidence", sa.Float),
        sa.Column("missing_information", sa.JSON, nullable=False),
        sa.Column("recovery_verified", sa.Boolean),
        sa.Column("baseline_minutes", sa.Integer, nullable=False),
        sa.Column("investigation_started_at", sa.DateTime(timezone=True)),
        sa.Column("recommendation_ready_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incidents_scenario_key", "incidents", ["scenario_key"])
    op.create_index("ix_incidents_service", "incidents", ["service"])
    op.create_index("ix_incidents_status", "incidents", ["status"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("data", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_incident_id", "evidence", ["incident_id"])

    op.create_table(
        "actions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments", sa.JSON, nullable=False),
        sa.Column("argument_hash", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("expected_result", sa.Text, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False, unique=True),
        sa.Column("approved_by", sa.String(160)),
        sa.Column("execution_result", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_actions_incident_id", "actions", ["incident_id"])
    op.create_index("ix_actions_status", "actions", ["status"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("action_id", sa.String(32), sa.ForeignKey("actions.id"), nullable=False),
        sa.Column("operator", sa.String(160), nullable=False),
        sa.Column("role", sa.String(80), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("approved_argument_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approvals_incident_id", "approvals", ["incident_id"])
    op.create_index("ix_approvals_action_id", "approvals", ["action_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("incident_id", sa.String(32), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_incident_id", "audit_events", ["incident_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("approvals")
    op.drop_table("actions")
    op.drop_table("evidence")
    op.drop_table("incidents")

