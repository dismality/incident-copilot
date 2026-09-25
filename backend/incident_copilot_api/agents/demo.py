from __future__ import annotations

from typing import Any

from ..schemas import EvidenceItem, InvestigationDecision, ProposedAction
from .base import InvestigationContext


def _number(data: dict[str, Any], *keys: str, default: float = 0) -> float:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int | float):
            return float(value)
    return default


class DemoInvestigator:
    """Deterministic, no-key mode that still exercises the complete workflow."""

    async def investigate(self, context: InvestigationContext) -> InvestigationDecision:
        service = context.alert.service
        health = await context.simulator.get_health(service)
        logs = await context.simulator.get_logs(service)
        deployments = await context.simulator.get_deployments(service)
        dependencies = await context.simulator.get_dependencies(service)

        evidence = [
            EvidenceItem(
                source="service_health",
                title="Current service health",
                detail=self._health_summary(health),
                data=health,
            ),
            EvidenceItem(
                source="logs",
                title="Recent sanitized logs",
                detail=self._log_summary(logs),
                data=logs,
            ),
            EvidenceItem(
                source="deployments",
                title="Recent deployment history",
                detail=self._deployment_summary(deployments),
                data=deployments,
            ),
            EvidenceItem(
                source="dependencies",
                title="Dependency health",
                detail=self._dependency_summary(dependencies),
                data=dependencies,
            ),
            EvidenceItem(
                source="runbook",
                title=f"Runbook: {context.scenario_key}",
                detail=context.runbook.split("\n", maxsplit=2)[-1][:700],
                data=None,
            ),
        ]

        # The incident type selects a relevant runbook, but the diagnosis is based
        # on the affected service and collected evidence rather than a root-cause
        # scenario name supplied by the dashboard.
        builders = {
            "checkout-api": self._bad_deployment,
            "search-api": self._traffic_surge,
            "reporting-worker": self._disk_pressure,
            "notification-service": self._provider_outage,
            "auth-service": self._ambiguous_login,
            "login-service": self._ambiguous_login,
        }
        builder = builders.get(context.alert.service, self._unknown)
        return builder(context, health, logs, deployments, dependencies, evidence)

    @staticmethod
    def _health_summary(health: dict[str, Any]) -> str:
        return (
            f"Status is {health.get('status', 'unknown')}; error rate "
            f"{_number(health, 'errorRate', 'error_rate'):.1%}; p95 latency "
            f"{_number(health, 'latencyMs', 'latency_ms'):.0f} ms."
        )

    @staticmethod
    def _log_summary(logs: list[dict[str, Any]]) -> str:
        messages = [str(item.get("message", "")) for item in logs[:3]]
        return " | ".join(messages) if messages else "No relevant log entries were returned."

    @staticmethod
    def _deployment_summary(deployments: list[dict[str, Any]]) -> str:
        if not deployments:
            return "No recent deployments were recorded."
        latest = deployments[0]
        return (
            f"Latest deployment is {latest.get('version', 'unknown')} with status "
            f"{latest.get('status', 'unknown')} at {latest.get('deployedAt', 'unknown time')}."
        )

    @staticmethod
    def _dependency_summary(dependencies: list[dict[str, Any]]) -> str:
        if not dependencies:
            return "No dependencies were returned."
        return ", ".join(
            f"{item.get('name', 'dependency')}={item.get('status', 'unknown')}"
            for item in dependencies
        )

    @staticmethod
    def _bad_deployment(context, health, logs, deployments, dependencies, evidence):
        log_text = " ".join(str(item.get("message", "")) for item in logs)
        dependencies_healthy = bool(dependencies) and all(
            str(item.get("status", "")).lower() == "healthy" for item in dependencies
        )
        if (
            len(deployments) < 2
            or "PaymentAdapterTimeout" not in log_text
            or not dependencies_healthy
        ):
            return InvestigationDecision(
                summary=(
                    "Checkout is degraded, but deployment timing, logs, and dependency "
                    "health do not yet support a safe root-cause decision."
                ),
                likely_cause=None,
                confidence=0.35,
                evidence=evidence,
                missing_information=[
                    "A confirmed failure signature",
                    "A known-good prior deployment",
                    "Complete dependency health",
                ],
                proposed_action=ProposedAction(
                    tool_name="gather_more_evidence",
                    arguments={},
                    risk_level="low",
                    reason="A symptom alone does not justify a production rollback.",
                    expected_result="A supported diagnosis before any infrastructure change.",
                ),
            )

        current_version = str(deployments[0].get("version", "unknown"))
        target_version = str(deployments[1].get("version", "unknown"))
        return InvestigationDecision(
            summary=(
                "The checkout failure began immediately after release "
                f"{current_version}, while the "
                "external payment provider remains healthy."
            ),
            likely_cause=f"Regression in checkout-api release {current_version}",
            confidence=0.94,
            evidence=evidence,
            missing_information=[],
            proposed_action=ProposedAction(
                tool_name="rollback_deployment",
                arguments={"targetVersion": target_version},
                risk_level="high",
                reason=(
                    "The failure is tightly correlated with the release and isolated "
                    "to changed code."
                ),
                expected_result="Error rate below 2% and p95 latency below 700 ms.",
            ),
        )

    @staticmethod
    def _traffic_surge(context, health, logs, deployments, dependencies, evidence):
        return InvestigationDecision(
            summary=(
                "Legitimate request volume has exceeded the search service's current capacity; "
                "dependencies remain healthy and there was no recent release."
            ),
            likely_cause="Capacity saturation caused by a legitimate traffic surge",
            confidence=0.91,
            evidence=evidence,
            missing_information=[],
            proposed_action=ProposedAction(
                tool_name="scale_service",
                arguments={"replicas": 10},
                risk_level="medium",
                reason=(
                    "Additional replicas address CPU saturation without changing application code."
                ),
                expected_result="CPU below 70% and p95 latency below 800 ms.",
            ),
        )

    @staticmethod
    def _disk_pressure(context, health, logs, deployments, dependencies, evidence):
        return InvestigationDecision(
            summary=(
                "Expired report exports are consuming the worker's disk; protected application "
                "and database paths are not implicated."
            ),
            likely_cause="Expired temporary exports exhausted available disk space",
            confidence=0.96,
            evidence=evidence,
            missing_information=[],
            proposed_action=ProposedAction(
                tool_name="cleanup_exports",
                arguments={"olderThanDays": 7},
                risk_level="high",
                reason="The runbook permits removal only from the temporary export directory.",
                expected_result="Free disk space above 25% with the worker healthy.",
            ),
        )

    @staticmethod
    def _provider_outage(context, health, logs, deployments, dependencies, evidence):
        return InvestigationDecision(
            summary=(
                "The notification service is healthy and messages are queued; the external email "
                "provider reports a regional outage."
            ),
            likely_cause="Confirmed outage at the external email provider",
            confidence=0.97,
            evidence=evidence,
            missing_information=[],
            proposed_action=ProposedAction(
                tool_name="monitor_only",
                arguments={},
                risk_level="low",
                reason=(
                    "Restarting a healthy internal service would not correct the provider outage."
                ),
                expected_result="Queued messages are delivered after the provider recovers.",
            ),
        )

    @staticmethod
    def _ambiguous_login(context, health, logs, deployments, dependencies, evidence):
        return InvestigationDecision(
            summary=(
                "A recent deployment, intermittent identity-provider errors, delayed logs, and "
                "mild database latency create several plausible causes."
            ),
            likely_cause=None,
            confidence=0.38,
            evidence=evidence,
            missing_information=[
                "Complete authentication logs",
                "Failure rate segmented by identity provider",
                "Login-specific database latency",
            ],
            proposed_action=ProposedAction(
                tool_name="gather_more_evidence",
                arguments={},
                risk_level="low",
                reason="Current evidence does not justify a restart or rollback.",
                expected_result="A supported diagnosis before any production-changing action.",
            ),
        )

    @staticmethod
    def _unknown(context, health, logs, deployments, dependencies, evidence):
        return InvestigationDecision(
            summary="The scenario is not recognized and no safe remediation can be selected.",
            likely_cause=None,
            confidence=0.1,
            evidence=evidence,
            missing_information=["A matching runbook and scenario-specific success criteria"],
            proposed_action=ProposedAction(
                tool_name="gather_more_evidence",
                arguments={},
                risk_level="low",
                reason="Unknown scenarios must fail closed.",
                expected_result="Human review provides a supported next step.",
            ),
        )
