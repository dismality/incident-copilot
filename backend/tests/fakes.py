from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

SCENARIOS: dict[str, dict[str, Any]] = {
    "bad-deployment": {
        "title": "Checkout failures after deployment",
        "description": "Release 2.8.1 introduced payment adapter timeouts.",
        "service": "checkout-api",
        "severity": "critical",
        "expectedOutcome": "Rollback to 2.8.0",
        "health": {
            "service": "checkout-api",
            "status": "degraded",
            "errorRate": 0.16,
            "latencyMs": 2400,
            "cpuPercent": 61,
            "diskFreePercent": 72,
            "replicas": 6,
            "version": "2.8.1",
        },
        "logs": [{"level": "ERROR", "message": "PaymentAdapterTimeout after release"}],
        "deployments": [
            {
                "version": "2.8.1",
                "status": "completed",
                "deployedAt": "2026-09-24T10:29:00Z",
            },
            {
                "version": "2.8.0",
                "status": "superseded",
                "deployedAt": "2026-09-20T09:00:00Z",
            },
        ],
        "dependencies": [{"name": "payment-provider", "status": "healthy"}],
    },
    "traffic-surge": {
        "title": "Search capacity saturation",
        "description": "Legitimate traffic exceeds current capacity.",
        "service": "search-api",
        "severity": "critical",
        "expectedOutcome": "Scale to ten replicas",
        "health": {
            "service": "search-api",
            "status": "degraded",
            "errorRate": 0.015,
            "latencyMs": 2200,
            "cpuPercent": 94,
            "diskFreePercent": 68,
            "replicas": 6,
            "version": "4.3.0",
        },
        "logs": [{"level": "WARN", "message": "Request volume is 4.1x baseline"}],
        "deployments": [],
        "dependencies": [{"name": "search-index", "status": "healthy"}],
    },
    "disk-pressure": {
        "title": "Reporting worker disk pressure",
        "description": "Expired exports consume local disk.",
        "service": "reporting-worker",
        "severity": "critical",
        "expectedOutcome": "Clean exports older than seven days",
        "health": {
            "service": "reporting-worker",
            "status": "degraded",
            "errorRate": 0.08,
            "latencyMs": 900,
            "cpuPercent": 44,
            "diskFreePercent": 4,
            "replicas": 2,
            "version": "1.9.0",
        },
        "logs": [{"level": "ERROR", "message": "No space left in /tmp/exports"}],
        "deployments": [],
        "dependencies": [],
    },
    "provider-outage": {
        "title": "Email provider outage",
        "description": "External provider is unavailable; messages are queued.",
        "service": "notification-service",
        "severity": "high",
        "expectedOutcome": "Monitor without internal restart",
        "health": {
            "service": "notification-service",
            "status": "healthy",
            "errorRate": 0.0,
            "latencyMs": 180,
            "cpuPercent": 31,
            "diskFreePercent": 81,
            "replicas": 3,
            "version": "3.1.2",
        },
        "logs": [{"level": "WARN", "message": "Provider returned HTTP 503; queued"}],
        "deployments": [],
        "dependencies": [{"name": "email-provider", "status": "outage"}],
    },
    "ambiguous-login": {
        "title": "Ambiguous login failures",
        "description": "Multiple plausible causes and incomplete telemetry.",
        "service": "login-service",
        "severity": "high",
        "expectedOutcome": "Gather more evidence",
        "health": {
            "service": "login-service",
            "status": "degraded",
            "errorRate": 0.08,
            "latencyMs": 870,
            "cpuPercent": 49,
            "diskFreePercent": 74,
            "replicas": 4,
            "version": "5.2.0",
        },
        "logs": [{"level": "WARN", "message": "Authentication logs delayed"}],
        "deployments": [{"version": "5.2.0", "status": "completed", "deployedAt": "recent"}],
        "dependencies": [
            {"name": "identity-provider", "status": "intermittent"},
            {"name": "sessions-db", "status": "degraded"},
        ],
    },
}


class FakeSimulator:
    def __init__(self) -> None:
        self.active_key = "bad-deployment"
        self.data = deepcopy(SCENARIOS[self.active_key])
        self.executions: dict[str, dict[str, Any]] = {}

    async def list_scenarios(self):
        return [
            {
                "key": key,
                "title": value["title"],
                "description": value["description"],
                "service": value["service"],
                "severity": value["severity"],
                "expectedOutcome": value["expectedOutcome"],
            }
            for key, value in SCENARIOS.items()
        ]

    async def start_scenario(self, scenario_key: str):
        self.active_key = scenario_key
        self.data = deepcopy(SCENARIOS[scenario_key])
        return {
            "scenarioKey": scenario_key,
            "title": self.data["title"],
            "description": self.data["description"],
            "alert": {
                "alertType": "simulated_alert",
                "service": self.data["service"],
                "environment": "production",
                "region": "ap-southeast-1",
                "severity": self.data["severity"],
                "summary": self.data["title"],
                "startedAt": datetime.now(UTC).isoformat(),
            },
        }

    async def get_health(self, service: str):
        assert service == self.data["service"]
        return deepcopy(self.data["health"])

    async def get_logs(self, service: str, minutes: int = 30):
        assert service == self.data["service"]
        return deepcopy(self.data["logs"])

    async def get_deployments(self, service: str):
        assert service == self.data["service"]
        return deepcopy(self.data["deployments"])

    async def get_dependencies(self, service: str):
        assert service == self.data["service"]
        return deepcopy(self.data["dependencies"])

    async def execute_action(
        self, *, service: str, tool_name: str, arguments: dict, idempotency_key: str
    ):
        if idempotency_key in self.executions:
            return deepcopy(self.executions[idempotency_key])
        health = self.data["health"]
        if tool_name == "rollback_deployment":
            health.update(
                status="healthy",
                errorRate=0.009,
                latencyMs=360,
                version=arguments["targetVersion"],
            )
        elif tool_name == "scale_service":
            health.update(
                status="healthy",
                cpuPercent=62,
                latencyMs=540,
                replicas=arguments["replicas"],
            )
        elif tool_name == "cleanup_exports":
            health.update(status="healthy", diskFreePercent=34, errorRate=0.0, latencyMs=310)
        elif tool_name == "restart_service":
            health.update(status="healthy", errorRate=0.0)
        result = {
            "success": True,
            "message": f"Executed {tool_name}",
            "idempotencyKey": idempotency_key,
            "health": deepcopy(health),
        }
        self.executions[idempotency_key] = result
        return deepcopy(result)
