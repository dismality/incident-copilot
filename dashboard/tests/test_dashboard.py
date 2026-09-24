from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

from api_client import ResolveOpsClient

INCIDENT = {
    "id": "inc-001",
    "title": "Checkout failures after deployment",
    "scenarioKey": "bad-deployment",
    "service": "checkout-api",
    "environment": "production",
    "region": "ap-southeast-1",
    "severity": "critical",
    "status": "awaiting_approval",
    "alertSummary": "Checkout error rate is 16% after deployment 2.8.1",
    "likelyCause": "Regression introduced by deployment 2.8.1",
    "confidence": 0.91,
    "summary": "Timing and payment adapter errors support a release regression.",
    "missingInformation": [],
    "recoveryVerified": False,
    "createdAt": "2026-09-24T10:32:00Z",
    "updatedAt": "2026-09-24T10:34:00Z",
    "evidence": [
        {
            "id": "ev-1",
            "source": "deployments",
            "title": "Recent release",
            "detail": "Version 2.8.1 preceded the error spike by three minutes.",
            "createdAt": "2026-09-24T10:33:00Z",
        }
    ],
    "actions": [
        {
            "id": "act-1",
            "toolName": "rollback_deployment",
            "arguments": {
                "service": "checkout-api",
                "environment": "production",
                "targetVersion": "2.8.0",
            },
            "riskLevel": "high",
            "status": "pending_approval",
            "reason": "The release is the strongest supported cause.",
            "expectedResult": "Error rate falls below 2%.",
            "approvedBy": None,
            "executionResult": None,
            "createdAt": "2026-09-24T10:34:00Z",
            "executedAt": None,
        }
    ],
    "approvals": [],
    "timeline": [
        {
            "id": "audit-1",
            "eventType": "alert_received",
            "actor": "monitor",
            "message": "Critical alert opened.",
            "details": {"severity": "critical"},
            "createdAt": "2026-09-24T10:32:00Z",
        }
    ],
}


def _response(method: str, url: str, payload: Any, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request(method, url),
    )


def smoke_dashboard_renders_connected_incident(monkeypatch) -> None:
    """Optional visual smoke check; invoke directly when changing the layout."""

    from streamlit.testing.v1 import AppTest

    def fake_request(method: str, url: str, **_: Any) -> httpx.Response:
        if url.endswith("/health"):
            return _response(method, url, {"status": "ok", "agentMode": "demo"})
        if url.endswith("/api/v1/scenarios"):
            return _response(
                method,
                url,
                [
                    {
                        "key": "bad-deployment",
                        "title": "Checkout failures after deployment",
                        "description": "A release introduced payment adapter timeouts.",
                    }
                ],
            )
        if url.endswith("/api/v1/incidents"):
            return _response(
                method,
                url,
                [
                    {
                        key: value
                        for key, value in INCIDENT.items()
                        if key not in {"evidence", "actions", "approvals", "timeline"}
                    }
                ],
            )
        if url.endswith("/api/v1/incidents/inc-001"):
            return _response(method, url, INCIDENT)
        if url.endswith("/api/v1/metrics"):
            return _response(
                method,
                url,
                {
                    "totalIncidents": 1,
                    "resolvedIncidents": 0,
                    "pendingApprovals": 1,
                    "approvalRate": 0.0,
                    "medianRecommendationSeconds": 12.4,
                    "simulatedTimeSavedPercent": 65.0,
                },
            )
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(httpx, "request", fake_request)
    dashboard = AppTest.from_file(DASHBOARD_DIR / "app.py", default_timeout=10).run()

    assert not dashboard.exception
    assert len(dashboard.metric) == 9
    assert any(button.key == "investigate_inc-001" for button in dashboard.button)
    assert any(button.key == "approve_act-1" for button in dashboard.button)


def test_approval_payload_is_bound_to_operator_role_and_comment(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        captured.update({"method": method, "url": url, **kwargs})
        return _response(method, url, INCIDENT)

    monkeypatch.setattr(httpx, "request", fake_request)
    client = ResolveOpsClient("http://control-plane:8000")
    client.approve_action(
        "act-1",
        operator="david@example.com",
        role="incident_commander",
        comment="Evidence supports rollback",
    )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/v1/actions/act-1/approve")
    assert captured["json"] == {
        "operator": "david@example.com",
        "role": "incident_commander",
        "comment": "Evidence supports rollback",
    }
