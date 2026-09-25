from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from incident_copilot_api.agents.demo import DemoInvestigator
from incident_copilot_api.config import Settings
from incident_copilot_api.database import Base
from incident_copilot_api.services.incidents import IncidentService

from .fakes import FakeSimulator


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def simulator():
    return FakeSimulator()


@pytest.fixture
def app_settings():
    return Settings(
        database_url="sqlite://",
        simulator_base_url="http://simulator.test",
        agent_mode="demo",
        alertmanager_webhook_token="test-monitoring-token",
        alertmanager_auto_investigate=False,
        runbook_directory=(__import__("pathlib").Path(__file__).resolve().parents[2] / "runbooks"),
    )


@pytest.fixture
def incident_service(db_session, simulator, app_settings):
    return IncidentService(
        db_session,
        app_settings,
        simulator,
        DemoInvestigator(),
    )
