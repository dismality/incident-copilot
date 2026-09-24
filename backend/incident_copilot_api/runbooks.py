from __future__ import annotations

from pathlib import Path


class RunbookNotFoundError(FileNotFoundError):
    pass


def load_runbook(directory: Path, scenario_key: str) -> str:
    """Load a scenario runbook while preventing path traversal."""

    safe_key = scenario_key.replace("_", "-")
    if not safe_key or any(part in safe_key for part in ("..", "/", "\\")):
        raise RunbookNotFoundError(f"Invalid runbook key: {scenario_key}")

    path = (directory / f"{safe_key}.md").resolve()
    root = directory.resolve()
    if root not in path.parents:
        raise RunbookNotFoundError(f"Runbook outside configured directory: {scenario_key}")
    if not path.exists():
        raise RunbookNotFoundError(f"No runbook for scenario: {scenario_key}")
    return path.read_text(encoding="utf-8")
