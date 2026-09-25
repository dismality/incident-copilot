"""Track external monitoring sources for deduplicated alert ingestion."""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("incidents") as batch:
        batch.add_column(
            sa.Column("source", sa.String(80), nullable=False, server_default="simulator")
        )
        batch.add_column(sa.Column("external_reference", sa.String(200), nullable=True))
        batch.create_index("ix_incidents_source", ["source"])
        batch.create_unique_constraint(
            "uq_incident_external_source", ["source", "external_reference"]
        )


def downgrade() -> None:
    with op.batch_alter_table("incidents") as batch:
        batch.drop_constraint("uq_incident_external_source", type_="unique")
        batch.drop_index("ix_incidents_source")
        batch.drop_column("external_reference")
        batch.drop_column("source")
