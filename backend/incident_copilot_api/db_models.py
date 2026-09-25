from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("source", "external_reference", name="uq_incident_external_source"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("inc"))
    title: Mapped[str] = mapped_column(String(200))
    scenario_key: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(80), default="simulator", index=True)
    external_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service: Mapped[str] = mapped_column(String(120), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    region: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    alert_summary: Mapped[str] = mapped_column(Text)
    alert_data: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    likely_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_information: Mapped[list] = mapped_column(JSON, default=list)
    recovery_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    baseline_minutes: Mapped[int] = mapped_column(Integer, default=20)
    investigation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recommendation_ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="Evidence.created_at"
    )
    actions: Mapped[list[Action]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="Action.created_at"
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="Approval.created_at"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="AuditEvent.created_at"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ev"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    source: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)
    data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="evidence")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("act"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    argument_hash: Mapped[str] = mapped_column(String(64))
    risk_level: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(40), default="pending_approval", index=True)
    reason: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="actions")
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("apr"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("actions.id"), index=True)
    operator: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(80))
    decision: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_argument_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="approvals")
    action: Mapped[Action] = relationship(back_populates="approvals")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("evt"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="audit_events")
