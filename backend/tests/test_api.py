from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from incident_copilot_api.agents.demo import DemoInvestigator
from incident_copilot_api.database import get_db


def test_http_workflow_exposes_typed_incident_and_metrics(
    db_session: Session,
    simulator,
    app_settings,
    monkeypatch,
) -> None:
    from incident_copilot_api import main as api

    def override_db() -> Generator[Session, None, None]:
        yield db_session

    monkeypatch.setattr(api, "settings", app_settings)
    monkeypatch.setattr(api, "simulator", simulator)
    monkeypatch.setattr(api, "investigator", DemoInvestigator())
    api.app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(api.app) as client:
            response = client.post("/api/v1/scenarios/bad-deployment/launch")
            assert response.status_code == 201
            incident = response.json()
            assert incident["status"] == "new"

            response = client.post(f"/api/v1/incidents/{incident['id']}/investigate")
            assert response.status_code == 200
            incident = response.json()
            action = incident["actions"][0]
            assert action["status"] == "pending_approval"
            assert action["arguments"]["targetVersion"] == "2.8.0"

            response = client.post(
                f"/api/v1/actions/{action['id']}/approve",
                json={
                    "operator": "commander@example.com",
                    "role": "incident_commander",
                    "comment": "Evidence supports an exact rollback.",
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "verifying"

            response = client.post(f"/api/v1/incidents/{incident['id']}/verify")
            assert response.status_code == 200
            assert response.json()["recoveryVerified"] is True

            response = client.post(
                f"/api/v1/incidents/{incident['id']}/notes",
                json={
                    "operator": "commander@example.com",
                    "role": "incident_commander",
                    "message": "Recovery confirmed with the payments owner.",
                },
            )
            assert response.status_code == 201
            note = response.json()["timeline"][-1]
            assert note["eventType"] == "operator_note"
            assert note["actor"] == "commander@example.com"
            assert note["message"] == "Recovery confirmed with the payments owner."
            assert note["details"]["role"] == "incident_commander"

            response = client.post(
                f"/api/v1/incidents/{incident['id']}/notes",
                json={
                    "operator": "commander@example.com",
                    "role": "incident_commander",
                    "message": "   ",
                },
            )
            assert response.status_code == 422

            response = client.post(
                "/api/v1/incidents/inc_missing/notes",
                json={
                    "operator": "commander@example.com",
                    "role": "incident_commander",
                    "message": "This incident does not exist.",
                },
            )
            assert response.status_code == 404

            metrics = client.get("/api/v1/metrics").json()
            assert metrics["totalIncidents"] == 1
            assert metrics["resolvedIncidents"] == 1
            assert "simulatedTimeSavedPercent" not in metrics
    finally:
        api.app.dependency_overrides.clear()
