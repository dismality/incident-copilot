from __future__ import annotations

import httpx
import pytest

from incident_copilot_api.simulator import SimulatorClient, SimulatorError


@pytest.mark.asyncio
async def test_transient_server_errors_are_retried():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, json={"message": "temporarily unavailable"})
        return httpx.Response(200, json={"status": "healthy"})

    client = SimulatorClient(
        "http://simulator.test",
        max_attempts=3,
        retry_delay_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    assert await client.get_health("checkout-api") == {"status": "healthy"}
    assert attempts == 3


@pytest.mark.asyncio
async def test_client_errors_fail_immediately_without_retry():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"message": "invalid request"})

    client = SimulatorClient(
        "http://simulator.test",
        max_attempts=3,
        retry_delay_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SimulatorError):
        await client.get_health("checkout-api")
    assert attempts == 1
