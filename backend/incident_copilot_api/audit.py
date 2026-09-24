from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .db_models import AuditEvent


def record_event(
    db: Session,
    *,
    incident_id: str,
    event_type: str,
    actor: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an immutable event to an incident's business audit trail."""

    event = AuditEvent(
        incident_id=incident_id,
        event_type=event_type,
        actor=actor,
        message=message,
        details=details or {},
    )
    db.add(event)
    return event
