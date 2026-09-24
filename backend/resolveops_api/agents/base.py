from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import Alert, InvestigationDecision
from ..simulator import SimulatorClient


@dataclass
class InvestigationContext:
    incident_id: str
    scenario_key: str
    alert: Alert
    runbook: str
    simulator: SimulatorClient


class Investigator(Protocol):
    async def investigate(self, context: InvestigationContext) -> InvestigationDecision: ...
