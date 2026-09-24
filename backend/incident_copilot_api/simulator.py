from __future__ import annotations

import asyncio
from typing import Any

import httpx


class SimulatorError(RuntimeError):
    pass


class SimulatorClient:
    """Typed gateway to the isolated Java infrastructure simulator."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        *,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_attempts = max(max_attempts, 1)
        self.retry_delay_seconds = max(retry_delay_seconds, 0)
        self.transport = transport

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                for attempt in range(1, self.max_attempts + 1):
                    try:
                        response = await client.request(method, path, params=params, json=json)
                    except (
                        httpx.ConnectError,
                        httpx.ReadError,
                        httpx.ReadTimeout,
                        httpx.RemoteProtocolError,
                        httpx.WriteError,
                    ):
                        if attempt >= self.max_attempts:
                            raise
                        await asyncio.sleep(self.retry_delay_seconds * 2 ** (attempt - 1))
                        continue

                    if response.status_code in {502, 503, 504} and attempt < self.max_attempts:
                        await asyncio.sleep(self.retry_delay_seconds * 2 ** (attempt - 1))
                        continue
                    response.raise_for_status()
                    return response.json()
                raise SimulatorError("Simulator retry loop ended without a response")
        except (httpx.HTTPError, ValueError) as exc:
            raise SimulatorError(f"Simulator request failed: {method} {path}: {exc}") from exc

    async def list_scenarios(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/scenarios")

    async def start_scenario(self, scenario_key: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/scenarios/{scenario_key}/start")

    async def get_health(self, service: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/services/{service}/health")

    async def get_logs(self, service: str, minutes: int = 30) -> list[dict[str, Any]]:
        return await self._request(
            "GET", f"/api/services/{service}/logs", params={"minutes": minutes}
        )

    async def get_deployments(self, service: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/api/services/{service}/deployments")

    async def get_dependencies(self, service: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/api/services/{service}/dependencies")

    async def execute_action(
        self,
        *,
        service: str,
        tool_name: str,
        arguments: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        endpoint_by_tool = {
            "rollback_deployment": "rollback",
            "scale_service": "scale",
            "restart_service": "restart",
            "cleanup_exports": "cleanup",
        }
        endpoint = endpoint_by_tool.get(tool_name)
        if endpoint is None:
            raise SimulatorError(f"Unsupported simulator action: {tool_name}")

        body = dict(arguments)
        body["idempotencyKey"] = idempotency_key
        return await self._request("POST", f"/api/services/{service}/actions/{endpoint}", json=body)
