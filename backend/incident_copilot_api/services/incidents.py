from __future__ import annotations

import statistics
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..agents.base import InvestigationContext, Investigator
from ..audit import record_event
from ..config import Settings
from ..db_models import Action, Approval, Evidence, Incident
from ..policy import (
    PolicyViolation,
    authorize_approval,
    authorize_history_logging,
    canonical_argument_hash,
    evaluate_proposal,
)
from ..runbooks import load_runbook
from ..schemas import (
    Alert,
    ApprovalRequest,
    IncidentNoteRequest,
    InvestigationDecision,
    MetricsResponse,
)
from ..simulator import SimulatorClient


class IncidentNotFoundError(LookupError):
    pass


class InvalidIncidentStateError(RuntimeError):
    pass


class IncidentService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        simulator: SimulatorClient,
        investigator: Investigator,
    ) -> None:
        self.db = db
        self.settings = settings
        self.simulator = simulator
        self.investigator = investigator

    async def list_scenarios(self) -> list[dict[str, Any]]:
        return await self.simulator.list_scenarios()

    async def launch_scenario(self, scenario_key: str) -> Incident:
        snapshot = await self.simulator.start_scenario(scenario_key)
        raw_alert = snapshot.get("alert", {})
        alert = Alert.model_validate(raw_alert)
        incident = Incident(
            title=str(snapshot.get("title", alert.summary)),
            scenario_key=scenario_key,
            service=alert.service,
            environment=alert.environment,
            region=alert.region,
            severity=alert.severity,
            status="new",
            alert_summary=alert.summary,
            alert_data=alert.model_dump(mode="json", by_alias=True),
        )
        self.db.add(incident)
        self.db.flush()
        record_event(
            self.db,
            incident_id=incident.id,
            event_type="alert_received",
            actor="monitoring-simulator",
            message=alert.summary,
            details={"scenarioKey": scenario_key, "severity": alert.severity},
        )
        self.db.commit()
        return self.get_incident(incident.id)

    def list_incidents(self) -> list[Incident]:
        stmt = (
            select(Incident)
            .options(selectinload(Incident.actions))
            .order_by(Incident.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_incident(self, incident_id: str) -> Incident:
        stmt = (
            select(Incident)
            .where(Incident.id == incident_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Incident.evidence),
                selectinload(Incident.actions),
                selectinload(Incident.approvals),
                selectinload(Incident.audit_events),
            )
        )
        incident = self.db.scalar(stmt)
        if incident is None:
            raise IncidentNotFoundError(incident_id)
        return incident

    async def investigate(self, incident_id: str) -> Incident:
        incident = self.get_incident(incident_id)
        investigable_states = {"new", "needs_evidence", "needs_human", "monitoring"}
        if incident.status not in investigable_states:
            raise InvalidIncidentStateError(
                f"Incident in status '{incident.status}' cannot be investigated"
            )

        incident.status = "investigating"
        incident.investigation_started_at = datetime.now(UTC)
        record_event(
            self.db,
            incident_id=incident.id,
            event_type="investigation_started",
            actor=f"agent:{self.settings.agent_mode}",
            message="Evidence collection and diagnosis started.",
            details={"agentMode": self.settings.agent_mode},
        )
        self.db.commit()

        alert = Alert.model_validate(incident.alert_data)
        runbook = load_runbook(self.settings.runbook_directory, incident.scenario_key)
        decision = await self.investigator.investigate(
            InvestigationContext(
                incident_id=incident.id,
                scenario_key=incident.scenario_key,
                alert=alert,
                runbook=runbook,
                simulator=self.simulator,
            )
        )
        self._persist_decision(incident, decision)
        self.db.commit()
        return self.get_incident(incident.id)

    def _persist_decision(self, incident: Incident, decision: InvestigationDecision) -> None:
        incident.summary = decision.summary
        incident.likely_cause = decision.likely_cause
        incident.confidence = decision.confidence
        incident.missing_information = decision.missing_information
        incident.recommendation_ready_at = datetime.now(UTC)

        for item in decision.evidence:
            self.db.add(
                Evidence(
                    incident_id=incident.id,
                    source=item.source,
                    title=item.title,
                    detail=item.detail,
                    data=item.data,
                )
            )

        policy = evaluate_proposal(
            decision.proposed_action,
            service=incident.service,
            environment=incident.environment,
        )
        tool_name = decision.proposed_action.tool_name
        if tool_name == "monitor_only":
            action_status = "not_required"
            incident.status = "monitoring"
        elif tool_name == "gather_more_evidence":
            action_status = "not_required"
            incident.status = "needs_evidence"
        else:
            action_status = "pending_approval" if policy.approval_required else "approved"
            incident.status = "awaiting_approval" if policy.approval_required else "approved"

        action_id = f"act_{uuid4().hex[:12]}"
        idempotency_key = f"{incident.id}:{action_id}:v1"
        argument_hash = canonical_argument_hash(tool_name, policy.normalized_arguments)
        action = Action(
            id=action_id,
            incident_id=incident.id,
            tool_name=tool_name,
            arguments=policy.normalized_arguments,
            argument_hash=argument_hash,
            risk_level=policy.risk_level,
            status=action_status,
            reason=decision.proposed_action.reason,
            expected_result=decision.proposed_action.expected_result,
            idempotency_key=idempotency_key,
        )
        self.db.add(action)
        record_event(
            self.db,
            incident_id=incident.id,
            event_type="recommendation_ready",
            actor=f"agent:{self.settings.agent_mode}",
            message=decision.summary,
            details={
                "likelyCause": decision.likely_cause,
                "confidence": decision.confidence,
                "proposedAction": tool_name,
                "riskLevel": policy.risk_level,
            },
        )
        if policy.approval_required:
            record_event(
                self.db,
                incident_id=incident.id,
                event_type="approval_requested",
                actor="policy-engine",
                message=f"{tool_name} requires an authorized human decision.",
                details={"actionId": action.id, "argumentHash": argument_hash},
            )

    async def approve_action(self, action_id: str, request: ApprovalRequest) -> Incident:
        action = self._get_action(action_id)
        if action.status != "pending_approval":
            raise InvalidIncidentStateError(
                f"Action in status '{action.status}' cannot be approved"
            )
        authorize_approval(action.tool_name, request.role)
        current_hash = canonical_argument_hash(action.tool_name, action.arguments)
        if current_hash != action.argument_hash:
            raise PolicyViolation("Action arguments changed after the approval request")

        approval = Approval(
            incident_id=action.incident_id,
            action_id=action.id,
            operator=request.operator,
            role=request.role,
            decision="approved",
            comment=request.comment,
            approved_argument_hash=current_hash,
        )
        self.db.add(approval)
        action.status = "approved"
        action.approved_by = request.operator
        action.incident.status = "executing"
        record_event(
            self.db,
            incident_id=action.incident_id,
            event_type="action_approved",
            actor=request.operator,
            message=f"Approved {action.tool_name} with unchanged arguments.",
            details={"actionId": action.id, "role": request.role},
        )
        self.db.commit()

        await self._execute(action.id)
        return self.get_incident(action.incident_id)

    def reject_action(self, action_id: str, request: ApprovalRequest) -> Incident:
        action = self._get_action(action_id)
        if action.status != "pending_approval":
            raise InvalidIncidentStateError(
                f"Action in status '{action.status}' cannot be rejected"
            )
        authorize_approval(action.tool_name, request.role)
        approval = Approval(
            incident_id=action.incident_id,
            action_id=action.id,
            operator=request.operator,
            role=request.role,
            decision="rejected",
            comment=request.comment,
            approved_argument_hash=action.argument_hash,
        )
        self.db.add(approval)
        action.status = "rejected"
        action.incident.status = "needs_human"
        record_event(
            self.db,
            incident_id=action.incident_id,
            event_type="action_rejected",
            actor=request.operator,
            message=f"Rejected {action.tool_name}; incident returned to human review.",
            details={"actionId": action.id, "role": request.role},
        )
        self.db.commit()
        return self.get_incident(action.incident_id)

    async def _execute(self, action_id: str) -> None:
        action = self._get_action(action_id)
        if action.status != "approved":
            raise InvalidIncidentStateError("Only approved actions can execute")

        approved = next((item for item in action.approvals if item.decision == "approved"), None)
        if approved is None or approved.approved_argument_hash != action.argument_hash:
            raise PolicyViolation("No valid approval is bound to these action arguments")

        tool_arguments = {
            key: value
            for key, value in action.arguments.items()
            if key not in {"service", "environment"}
        }
        try:
            result = await self.simulator.execute_action(
                service=action.incident.service,
                tool_name=action.tool_name,
                arguments=tool_arguments,
                idempotency_key=action.idempotency_key,
            )
        except Exception as exc:
            action.status = "failed"
            action.execution_result = {"success": False, "error": str(exc)}
            action.executed_at = datetime.now(UTC)
            action.incident.status = "needs_human"
            record_event(
                self.db,
                incident_id=action.incident_id,
                event_type="action_failed",
                actor="execution-engine",
                message=f"{action.tool_name} failed safely.",
                details={"actionId": action.id, "error": str(exc)},
            )
            self.db.commit()
            return

        if not bool(result.get("success")):
            action.status = "failed"
            action.execution_result = result
            action.executed_at = datetime.now(UTC)
            action.incident.status = "needs_human"
            record_event(
                self.db,
                incident_id=action.incident_id,
                event_type="action_failed",
                actor="execution-engine",
                message=f"{action.tool_name} was rejected or did not complete successfully.",
                details={"actionId": action.id, "result": result},
            )
            self.db.commit()
            return

        action.status = "executed"
        action.execution_result = result
        action.executed_at = datetime.now(UTC)
        action.incident.status = "verifying"
        record_event(
            self.db,
            incident_id=action.incident_id,
            event_type="action_executed",
            actor="execution-engine",
            message=f"Executed {action.tool_name}; recovery still requires verification.",
            details={"actionId": action.id, "result": result},
        )
        self.db.commit()

    async def verify(self, incident_id: str) -> Incident:
        incident = self.get_incident(incident_id)
        if incident.status not in {"verifying", "monitoring", "needs_evidence", "needs_human"}:
            raise InvalidIncidentStateError(
                f"Incident in status '{incident.status}' is not ready for verification"
            )
        health = await self.simulator.get_health(incident.service)
        success, explanation = self._verification_result(incident.scenario_key, health)
        incident.recovery_verified = success
        if success:
            incident.status = "resolved"
            incident.resolved_at = datetime.now(UTC)
            event_type = "recovery_verified"
        elif incident.scenario_key in {"provider-outage", "ambiguous-login"}:
            incident.status = (
                "monitoring" if incident.scenario_key == "provider-outage" else "needs_evidence"
            )
            event_type = "verification_inconclusive"
        else:
            incident.status = "needs_human"
            event_type = "verification_failed"
        record_event(
            self.db,
            incident_id=incident.id,
            event_type=event_type,
            actor="verification-engine",
            message=explanation,
            details={"health": health, "recoveryVerified": success},
        )
        self.db.commit()
        return self.get_incident(incident.id)

    def add_note(self, incident_id: str, request: IncidentNoteRequest) -> Incident:
        incident = self.get_incident(incident_id)
        authorize_history_logging(request.role)
        record_event(
            self.db,
            incident_id=incident.id,
            event_type="operator_note",
            actor=request.operator,
            message=request.message,
            details={"role": request.role, "source": "operator"},
        )
        incident.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.get_incident(incident.id)

    @staticmethod
    def _verification_result(scenario_key: str, health: dict[str, Any]) -> tuple[bool, str]:
        status = str(health.get("status", "unknown")).lower()
        error_rate = float(health.get("errorRate", health.get("error_rate", 1)))
        latency = float(health.get("latencyMs", health.get("latency_ms", 99999)))
        cpu = float(health.get("cpuPercent", health.get("cpu_percent", 100)))
        disk_free = float(health.get("diskFreePercent", health.get("disk_free_percent", 0)))

        if scenario_key == "bad-deployment":
            ok = status == "healthy" and error_rate < 0.02 and latency < 700
            return ok, (
                "Recovery verified: checkout health returned within the runbook thresholds."
                if ok
                else "Rollback executed, but checkout health remains outside safe thresholds."
            )
        if scenario_key == "traffic-surge":
            ok = status == "healthy" and cpu < 70 and latency < 800
            return ok, (
                "Recovery verified: capacity and latency returned within thresholds."
                if ok
                else "Scaling completed, but capacity thresholds are still not satisfied."
            )
        if scenario_key == "disk-pressure":
            ok = status == "healthy" and disk_free >= 25
            return ok, (
                "Recovery verified: free disk space is above 25% and the worker is healthy."
                if ok
                else "Cleanup completed, but disk or worker health remains unsafe."
            )
        if scenario_key == "provider-outage":
            return False, "Internal service is stable; continue monitoring the external provider."
        return False, "Evidence remains insufficient for a verified recovery decision."

    def metrics(self) -> MetricsResponse:
        incidents = list(self.db.scalars(select(Incident)).all())
        total = len(incidents)
        resolved = sum(item.status == "resolved" for item in incidents)
        pending = int(
            self.db.scalar(
                select(func.count()).select_from(Action).where(Action.status == "pending_approval")
            )
            or 0
        )
        decisions = list(self.db.scalars(select(Approval)).all())
        approved = sum(item.decision == "approved" for item in decisions)
        approval_rate = approved / len(decisions) if decisions else 0.0

        recommendation_seconds: list[float] = []
        for item in incidents:
            if item.investigation_started_at and item.recommendation_ready_at:
                start = self._as_utc(item.investigation_started_at)
                end = self._as_utc(item.recommendation_ready_at)
                seconds = max((end - start).total_seconds(), 0)
                recommendation_seconds.append(seconds)

        return MetricsResponse(
            total_incidents=total,
            resolved_incidents=resolved,
            pending_approvals=pending,
            approval_rate=round(approval_rate, 3),
            median_recommendation_seconds=round(statistics.median(recommendation_seconds), 2)
            if recommendation_seconds
            else 0.0,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    def _get_action(self, action_id: str) -> Action:
        stmt = (
            select(Action)
            .where(Action.id == action_id)
            .execution_options(populate_existing=True)
            .options(selectinload(Action.incident), selectinload(Action.approvals))
        )
        action = self.db.scalar(stmt)
        if action is None:
            raise IncidentNotFoundError(action_id)
        return action
