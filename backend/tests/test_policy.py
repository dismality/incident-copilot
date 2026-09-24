from __future__ import annotations

import pytest

from resolveops_api.policy import (
    PolicyViolation,
    authorize_approval,
    canonical_argument_hash,
    evaluate_proposal,
)
from resolveops_api.schemas import ProposedAction


def proposal(tool: str, arguments: dict) -> ProposedAction:
    return ProposedAction(
        toolName=tool,
        arguments=arguments,
        riskLevel="high",
        reason="Test",
        expectedResult="Healthy",
    )


def test_rollback_arguments_are_normalized():
    decision = evaluate_proposal(
        proposal("rollback_deployment", {"targetVersion": "2.8.0", "ignored": "value"}),
        service="checkout-api",
        environment="production",
    )
    assert decision.risk_level == "high"
    assert decision.normalized_arguments == {
        "targetVersion": "2.8.0",
        "service": "checkout-api",
        "environment": "production",
    }


@pytest.mark.parametrize("replicas", [0, 21, -5, "ten", True])
def test_scaling_outside_policy_is_rejected(replicas):
    with pytest.raises(PolicyViolation):
        evaluate_proposal(
            proposal("scale_service", {"replicas": replicas}),
            service="search-api",
            environment="production",
        )


@pytest.mark.parametrize("target", ["", "../2.8.0", "2.8.0;restart", "version with spaces"])
def test_rollback_target_must_be_a_safe_version_identifier(target):
    with pytest.raises(PolicyViolation):
        evaluate_proposal(
            proposal("rollback_deployment", {"targetVersion": target}),
            service="checkout-api",
            environment="production",
        )


def test_viewer_cannot_approve_production_change():
    with pytest.raises(PolicyViolation):
        authorize_approval("rollback_deployment", "viewer")


def test_argument_hash_binds_tool_and_exact_arguments():
    first = canonical_argument_hash("scale_service", {"replicas": 10})
    same = canonical_argument_hash("scale_service", {"replicas": 10})
    changed = canonical_argument_hash("scale_service", {"replicas": 11})
    assert first == same
    assert first != changed


def test_unknown_action_fails_closed():
    raw = {
        "toolName": "restart_service",
        "arguments": {},
        "riskLevel": "medium",
        "reason": "Test",
        "expectedResult": "Healthy",
    }
    valid = ProposedAction.model_validate(raw)
    valid.tool_name = "delete_database"  # type: ignore[assignment]
    with pytest.raises(PolicyViolation):
        evaluate_proposal(valid, service="orders-db", environment="production")
