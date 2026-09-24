from __future__ import annotations

import pytest

from incident_copilot_api.policy import PolicyViolation
from incident_copilot_api.schemas import ApprovalRequest
from incident_copilot_api.services.incidents import InvalidIncidentStateError


@pytest.mark.asyncio
async def test_bad_deployment_can_be_approved_executed_and_verified(incident_service):
    incident = await incident_service.launch_scenario("bad-deployment")
    assert incident.status == "new"

    incident = await incident_service.investigate(incident.id)
    action = incident.actions[0]
    assert incident.status == "awaiting_approval"
    assert action.tool_name == "rollback_deployment"
    assert action.status == "pending_approval"

    incident = await incident_service.approve_action(
        action.id,
        ApprovalRequest(
            operator="oncall@example.com",
            role="incident_commander",
            comment="Timing and logs support rollback.",
        ),
    )
    assert incident.status == "verifying"
    assert incident.actions[0].status == "executed"

    incident = await incident_service.verify(incident.id)
    assert incident.status == "resolved"
    assert incident.recovery_verified is True
    event_types = [event.event_type for event in incident.audit_events]
    assert event_types == [
        "alert_received",
        "investigation_started",
        "recommendation_ready",
        "approval_requested",
        "action_approved",
        "action_executed",
        "recovery_verified",
    ]


@pytest.mark.asyncio
async def test_provider_outage_does_not_create_executable_action(incident_service):
    incident = await incident_service.launch_scenario("provider-outage")
    incident = await incident_service.investigate(incident.id)
    assert incident.status == "monitoring"
    assert incident.actions[0].tool_name == "monitor_only"
    assert incident.actions[0].status == "not_required"


@pytest.mark.asyncio
async def test_ambiguous_incident_refuses_to_act(incident_service):
    incident = await incident_service.launch_scenario("ambiguous-login")
    incident = await incident_service.investigate(incident.id)
    assert incident.status == "needs_evidence"
    assert incident.likely_cause is None
    assert incident.confidence < 0.5
    assert len(incident.missing_information) == 3


@pytest.mark.asyncio
async def test_rejected_action_returns_to_human_review(incident_service):
    incident = await incident_service.launch_scenario("traffic-surge")
    incident = await incident_service.investigate(incident.id)
    action = incident.actions[0]
    incident = incident_service.reject_action(
        action.id,
        ApprovalRequest(
            operator="commander@example.com",
            role="incident_commander",
            comment="Cost increase requires capacity review.",
        ),
    )
    assert incident.status == "needs_human"
    assert incident.actions[0].status == "rejected"


@pytest.mark.asyncio
async def test_duplicate_approval_is_rejected(incident_service):
    incident = await incident_service.launch_scenario("disk-pressure")
    incident = await incident_service.investigate(incident.id)
    action_id = incident.actions[0].id
    approval = ApprovalRequest(
        operator="oncall@example.com", role="platform_engineer", comment="Approved"
    )
    await incident_service.approve_action(action_id, approval)
    with pytest.raises(InvalidIncidentStateError):
        await incident_service.approve_action(action_id, approval)


@pytest.mark.asyncio
async def test_second_investigation_is_blocked_while_approval_is_pending(incident_service):
    incident = await incident_service.launch_scenario("bad-deployment")
    incident = await incident_service.investigate(incident.id)

    with pytest.raises(InvalidIncidentStateError):
        await incident_service.investigate(incident.id)


@pytest.mark.asyncio
async def test_unsuccessful_tool_result_fails_closed(incident_service, monkeypatch):
    incident = await incident_service.launch_scenario("bad-deployment")
    incident = await incident_service.investigate(incident.id)
    action = incident.actions[0]

    async def unsuccessful_execution(**_):
        return {
            "success": False,
            "message": "Target version is not available.",
            "idempotencyKey": "test-key",
        }

    monkeypatch.setattr(incident_service.simulator, "execute_action", unsuccessful_execution)
    incident = await incident_service.approve_action(
        action.id,
        ApprovalRequest(
            operator="oncall@example.com",
            role="incident_commander",
            comment="Approved after evidence review.",
        ),
    )

    assert incident.status == "needs_human"
    assert incident.actions[0].status == "failed"
    assert incident.actions[0].execution_result["success"] is False
    assert incident.audit_events[-1].event_type == "action_failed"


@pytest.mark.asyncio
async def test_unauthorized_role_cannot_approve(incident_service):
    incident = await incident_service.launch_scenario("bad-deployment")
    incident = await incident_service.investigate(incident.id)
    with pytest.raises(PolicyViolation):
        await incident_service.approve_action(
            incident.actions[0].id,
            ApprovalRequest(operator="viewer@example.com", role="viewer"),
        )


@pytest.mark.asyncio
async def test_metrics_are_explicitly_simulated(incident_service):
    incident = await incident_service.launch_scenario("bad-deployment")
    await incident_service.investigate(incident.id)
    metrics = incident_service.metrics()
    assert metrics.total_incidents == 1
    assert metrics.pending_approvals == 1
    assert 0 <= metrics.simulated_time_saved_percent <= 100
