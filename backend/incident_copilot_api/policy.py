from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .schemas import ProposedAction


class PolicyViolation(ValueError):
    pass


@dataclass(frozen=True)
class ActionPolicy:
    risk_level: str
    approval_required: bool
    permitted_roles: frozenset[str]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    approval_required: bool
    risk_level: str
    reason: str
    normalized_arguments: dict[str, Any]


ACTION_POLICIES = {
    "rollback_deployment": ActionPolicy(
        risk_level="high",
        approval_required=True,
        permitted_roles=frozenset({"incident_commander", "platform_engineer"}),
    ),
    "scale_service": ActionPolicy(
        risk_level="medium",
        approval_required=True,
        permitted_roles=frozenset({"incident_commander", "platform_engineer"}),
    ),
    "restart_service": ActionPolicy(
        risk_level="medium",
        approval_required=True,
        permitted_roles=frozenset({"incident_commander", "platform_engineer"}),
    ),
    "cleanup_exports": ActionPolicy(
        risk_level="high",
        approval_required=True,
        permitted_roles=frozenset({"incident_commander", "platform_engineer"}),
    ),
}

HISTORY_LOG_ROLES = frozenset({"incident_commander", "platform_engineer"})


def canonical_argument_hash(tool_name: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps(
        {"tool": tool_name, "arguments": arguments}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate_proposal(
    proposal: ProposedAction,
    *,
    service: str,
    environment: str,
) -> PolicyDecision:
    if proposal.tool_name in {"monitor_only", "gather_more_evidence"}:
        return PolicyDecision(
            allowed=True,
            approval_required=False,
            risk_level="low",
            reason="Read-only operational decision",
            normalized_arguments={},
        )

    policy = ACTION_POLICIES.get(proposal.tool_name)
    if policy is None:
        raise PolicyViolation(f"Action is not allowlisted: {proposal.tool_name}")
    if environment not in {"development", "staging", "production"}:
        raise PolicyViolation(f"Environment is not allowlisted: {environment}")

    args = dict(proposal.arguments)
    args["service"] = service
    args["environment"] = environment

    if proposal.tool_name == "rollback_deployment":
        target = args.get("targetVersion") or args.get("target_version")
        if (
            not isinstance(target, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", target) is None
        ):
            raise PolicyViolation("A valid targetVersion is required for rollback")
        args = {"targetVersion": target, "service": service, "environment": environment}
    elif proposal.tool_name == "scale_service":
        replicas = args.get("replicas")
        if type(replicas) is not int or not 1 <= replicas <= 20:
            raise PolicyViolation("Replica count must be between 1 and 20")
        args = {"replicas": replicas, "service": service, "environment": environment}
    elif proposal.tool_name == "restart_service":
        args = {"service": service, "environment": environment}
    elif proposal.tool_name == "cleanup_exports":
        days = args.get("olderThanDays", args.get("older_than_days"))
        if type(days) is not int or not 1 <= days <= 30:
            raise PolicyViolation("Cleanup retention must be between 1 and 30 days")
        args = {"olderThanDays": days, "service": service, "environment": environment}

    return PolicyDecision(
        allowed=True,
        approval_required=policy.approval_required,
        risk_level=policy.risk_level,
        reason="Action is allowlisted and arguments satisfy deterministic policy",
        normalized_arguments=args,
    )


def authorize_approval(tool_name: str, role: str) -> None:
    policy = ACTION_POLICIES.get(tool_name)
    if policy is None:
        raise PolicyViolation(f"Action is not approvable: {tool_name}")
    if role not in policy.permitted_roles:
        raise PolicyViolation(f"Role '{role}' cannot approve {tool_name}")


def authorize_history_logging(role: str) -> None:
    if role not in HISTORY_LOG_ROLES:
        raise PolicyViolation(f"Role '{role}' cannot add incident history entries")
