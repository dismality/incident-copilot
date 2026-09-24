from __future__ import annotations

import pytest

from resolveops_api.agents.demo import DemoInvestigator
from resolveops_api.agents.factory import build_investigator
from resolveops_api.policy import PolicyViolation, evaluate_proposal
from resolveops_api.runbooks import RunbookNotFoundError, load_runbook
from resolveops_api.schemas import ProposedAction
from resolveops_api.serializers import incident_detail, incident_summary


def make_proposal(tool_name: str, arguments: dict) -> ProposedAction:
    return ProposedAction(
        toolName=tool_name,
        arguments=arguments,
        riskLevel="medium",
        reason="A supported test proposal",
        expectedResult="A measurable result",
    )


def test_demo_factory_is_offline_by_default(app_settings):
    assert isinstance(build_investigator(app_settings), DemoInvestigator)


def test_invalid_and_missing_runbook_paths_fail_closed(app_settings):
    with pytest.raises(RunbookNotFoundError):
        load_runbook(app_settings.runbook_directory, "../secrets")
    with pytest.raises(RunbookNotFoundError):
        load_runbook(app_settings.runbook_directory, "does-not-exist")


def test_low_risk_decision_requires_no_approval():
    decision = evaluate_proposal(
        make_proposal("monitor_only", {}),
        service="notification-service",
        environment="production",
    )
    assert decision.allowed
    assert not decision.approval_required


def test_cleanup_and_restart_are_normalized():
    cleanup = evaluate_proposal(
        make_proposal("cleanup_exports", {"olderThanDays": 7, "path": "C:/unsafe"}),
        service="reporting-worker",
        environment="production",
    )
    assert cleanup.normalized_arguments["olderThanDays"] == 7
    assert "path" not in cleanup.normalized_arguments

    restart = evaluate_proposal(
        make_proposal("restart_service", {"unexpected": "ignored"}),
        service="worker",
        environment="staging",
    )
    assert restart.normalized_arguments == {
        "service": "worker",
        "environment": "staging",
    }


def test_invalid_cleanup_retention_is_rejected():
    with pytest.raises(PolicyViolation):
        evaluate_proposal(
            make_proposal("cleanup_exports", {"olderThanDays": 60}),
            service="reporting-worker",
            environment="production",
        )


@pytest.mark.asyncio
async def test_incident_serializers_include_nested_timeline(incident_service):
    incident = await incident_service.launch_scenario("provider-outage")
    incident = await incident_service.investigate(incident.id)
    summary = incident_summary(incident)
    detail = incident_detail(incident)
    assert summary.id == incident.id
    assert detail.timeline[0].event_type == "alert_received"
    assert detail.actions[0].tool_name == "monitor_only"
    assert len(detail.evidence) == 5
