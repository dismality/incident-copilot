from __future__ import annotations

from .db_models import Incident
from .schemas import (
    ActionResponse,
    ApprovalResponse,
    AuditEventResponse,
    EvidenceResponse,
    IncidentDetail,
    IncidentSummary,
)


def incident_summary(incident: Incident) -> IncidentSummary:
    return IncidentSummary.model_validate(incident)


def incident_detail(incident: Incident) -> IncidentDetail:
    base = IncidentSummary.model_validate(incident).model_dump()
    return IncidentDetail(
        **base,
        summary=incident.summary,
        missing_information=incident.missing_information or [],
        evidence=[EvidenceResponse.model_validate(item) for item in incident.evidence],
        actions=[ActionResponse.model_validate(item) for item in incident.actions],
        approvals=[ApprovalResponse.model_validate(item) for item in incident.approvals],
        timeline=[AuditEventResponse.model_validate(item) for item in incident.audit_events],
    )
