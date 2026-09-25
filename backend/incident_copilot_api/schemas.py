from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=lambda value: "".join(
            word if index == 0 else word.capitalize() for index, word in enumerate(value.split("_"))
        ),
    )


class Alert(CamelModel):
    alert_type: str
    service: str
    environment: str
    region: str
    severity: str
    summary: str
    started_at: datetime | str


class ScenarioSummary(CamelModel):
    key: str
    title: str
    description: str
    service: str
    severity: str
    expected_outcome: str


class EvidenceItem(CamelModel):
    source: str
    title: str
    detail: str
    data: dict[str, Any] | list[Any] | None = None


class ProposedAction(CamelModel):
    tool_name: Literal[
        "rollback_deployment",
        "scale_service",
        "restart_service",
        "cleanup_exports",
        "monitor_only",
        "gather_more_evidence",
    ]
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "high", "prohibited"]
    reason: str
    expected_result: str


class InvestigationDecision(CamelModel):
    summary: str
    likely_cause: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem]
    missing_information: list[str] = Field(default_factory=list)
    proposed_action: ProposedAction


class EvidenceResponse(CamelModel):
    id: str
    source: str
    title: str
    detail: str
    data: dict[str, Any] | list[Any] | None = None
    created_at: datetime


class ActionResponse(CamelModel):
    id: str
    tool_name: str
    arguments: dict[str, Any]
    risk_level: str
    status: str
    reason: str
    expected_result: str
    approved_by: str | None = None
    execution_result: dict[str, Any] | None = None
    created_at: datetime
    executed_at: datetime | None = None


class ApprovalResponse(CamelModel):
    id: str
    action_id: str
    operator: str
    role: str
    decision: str
    comment: str | None = None
    created_at: datetime


class AuditEventResponse(CamelModel):
    id: str
    event_type: str
    actor: str
    message: str
    details: dict[str, Any]
    created_at: datetime


class IncidentSummary(CamelModel):
    id: str
    title: str
    scenario_key: str
    source: str
    external_reference: str | None = None
    service: str
    environment: str
    region: str
    severity: str
    status: str
    alert_summary: str
    likely_cause: str | None = None
    confidence: float | None = None
    recovery_verified: bool | None = None
    created_at: datetime
    updated_at: datetime


class IncidentDetail(IncidentSummary):
    summary: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    actions: list[ActionResponse] = Field(default_factory=list)
    approvals: list[ApprovalResponse] = Field(default_factory=list)
    timeline: list[AuditEventResponse] = Field(default_factory=list)


class ApprovalRequest(CamelModel):
    operator: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=80)
    comment: str | None = Field(default=None, max_length=1000)


class IncidentNoteRequest(CamelModel):
    operator: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("operator", "role", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class AlertmanagerAlert(CamelModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    starts_at: datetime | str
    ends_at: datetime | str | None = None
    generator_url: str | None = Field(default=None, alias="generatorURL")
    fingerprint: str = Field(min_length=1, max_length=200)

    @field_validator("labels", "annotations")
    @classmethod
    def bound_monitoring_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 50:
            raise ValueError("must contain no more than 50 entries")
        if any(len(key) > 160 or len(item) > 4000 for key, item in value.items()):
            raise ValueError("monitoring metadata is too large")
        return value


class AlertmanagerWebhook(CamelModel):
    version: str
    group_key: str = Field(max_length=500)
    status: Literal["firing", "resolved"]
    receiver: str = Field(max_length=160)
    alerts: list[AlertmanagerAlert] = Field(min_length=1, max_length=50)


class AlertmanagerIngestionResponse(CamelModel):
    created_incident_ids: list[str] = Field(default_factory=list)
    deduplicated_incident_ids: list[str] = Field(default_factory=list)
    resolved_incident_ids: list[str] = Field(default_factory=list)
    ignored_alerts: list[str] = Field(default_factory=list)


class ScenarioInjectionResponse(CamelModel):
    scenario_key: str
    title: str
    description: str
    detection_status: Literal["awaiting_prometheus"] = "awaiting_prometheus"


class MetricsResponse(CamelModel):
    total_incidents: int
    resolved_incidents: int
    pending_approvals: int
    approval_rate: float
    median_recommendation_seconds: float


class HealthResponse(CamelModel):
    status: str
    agent_mode: str
    simulator_url: str
