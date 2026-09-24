from __future__ import annotations

from ..config import Settings
from .base import Investigator
from .demo import DemoInvestigator


def build_investigator(settings: Settings) -> Investigator:
    if settings.agent_mode == "demo":
        return DemoInvestigator()

    from .openai_agent import OpenAIInvestigator

    return OpenAIInvestigator(model=settings.openai_model)
