"""Small, defensive HTTP client for the Incident Copilot control plane.

Nothing in this module performs network I/O at import time.  Keeping the
client separate from the Streamlit view also makes the dashboard easy to test
with a mock transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class ControlPlaneError(RuntimeError):
    """A user-presentable error returned while calling the control plane."""

    message: str
    endpoint: str
    status_code: int | None = None
    detail: str | None = None

    def __str__(self) -> str:
        return self.message


class IncidentCopilotClient:
    """Typed facade over the dashboard-facing control-plane endpoints."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 2.0))

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        endpoint = f"{self.base_url}{path}"
        try:
            response = httpx.request(
                method,
                endpoint,
                json=json,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ControlPlaneError(
                "The control plane did not respond in time.", endpoint
            ) from exc
        except httpx.ConnectError as exc:
            raise ControlPlaneError(
                "The control plane is offline or unreachable.", endpoint
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = _error_detail(exc.response)
            raise ControlPlaneError(
                _status_message(exc.response.status_code),
                endpoint,
                status_code=exc.response.status_code,
                detail=detail,
            ) from exc
        except httpx.HTTPError as exc:
            raise ControlPlaneError(
                "The control plane request could not be completed.",
                endpoint,
                detail=str(exc),
            ) from exc

        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ControlPlaneError(
                "The control plane returned an unreadable response.", endpoint
            ) from exc

    def health(self) -> dict[str, Any]:
        value = self._request("GET", "/health")
        return value if isinstance(value, dict) else {"status": "unknown"}

    def scenarios(self) -> list[dict[str, Any]]:
        return _as_list(self._request("GET", "/api/v1/scenarios"), "scenarios")

    def launch_scenario(self, scenario_key: str) -> dict[str, Any]:
        value = self._request("POST", f"/api/v1/scenarios/{scenario_key}/launch")
        return _as_object(value, "incident")

    def incidents(self) -> list[dict[str, Any]]:
        return _as_list(self._request("GET", "/api/v1/incidents"), "incidents")

    def incident(self, incident_id: str) -> dict[str, Any]:
        value = self._request("GET", f"/api/v1/incidents/{incident_id}")
        return _as_object(value, "incident")

    def investigate(self, incident_id: str) -> dict[str, Any]:
        value = self._request("POST", f"/api/v1/incidents/{incident_id}/investigate")
        return _as_object(value, "incident")

    def approve_action(
        self,
        action_id: str,
        *,
        operator: str,
        role: str,
        comment: str,
    ) -> dict[str, Any]:
        value = self._request(
            "POST",
            f"/api/v1/actions/{action_id}/approve",
            json={"operator": operator, "role": role, "comment": comment},
        )
        return _as_object(value, "incident")

    def reject_action(
        self,
        action_id: str,
        *,
        operator: str,
        role: str,
        comment: str,
    ) -> dict[str, Any]:
        value = self._request(
            "POST",
            f"/api/v1/actions/{action_id}/reject",
            json={"operator": operator, "role": role, "comment": comment},
        )
        return _as_object(value, "incident")

    def verify(self, incident_id: str) -> dict[str, Any]:
        value = self._request("POST", f"/api/v1/incidents/{incident_id}/verify")
        return _as_object(value, "incident")

    def add_note(
        self,
        incident_id: str,
        *,
        operator: str,
        role: str,
        message: str,
    ) -> dict[str, Any]:
        value = self._request(
            "POST",
            f"/api/v1/incidents/{incident_id}/notes",
            json={"operator": operator, "role": role, "message": message},
        )
        return _as_object(value, "incident")

    def metrics(self) -> dict[str, Any]:
        value = self._request("GET", "/api/v1/metrics")
        return _as_object(value, "metrics")


def _as_list(value: Any, key: str) -> list[dict[str, Any]]:
    """Accept either a bare list or common envelope formats."""

    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        candidates = (value.get(key), value.get("items"), value.get("data"))
        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def _as_object(value: Any, key: str) -> dict[str, Any]:
    """Accept a bare object or an object wrapped by a conventional key."""

    if not isinstance(value, dict):
        return {}
    nested = value.get(key)
    if isinstance(nested, dict):
        return nested
    data = value.get("data")
    if isinstance(data, dict):
        return data
    return value


def _error_detail(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:300] if text else None
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail)[:500]
        if detail is not None:
            return str(detail)[:500]
    return str(payload)[:500]


def _status_message(status_code: int) -> str:
    if status_code == 400:
        return "The control plane rejected this request."
    if status_code == 401:
        return "Authentication is required."
    if status_code == 403:
        return "You are not authorized to perform this action."
    if status_code == 404:
        return "The requested incident or action no longer exists."
    if status_code == 409:
        return "This action conflicts with the incident's current state."
    if status_code == 422:
        return "The submitted operator decision is incomplete or invalid."
    if status_code >= 500:
        return "The control plane encountered an internal error."
    return f"The control plane returned HTTP {status_code}."
