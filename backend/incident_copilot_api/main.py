from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agents import build_investigator
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .policy import PolicyViolation
from .schemas import (
    AlertmanagerIngestionResponse,
    AlertmanagerWebhook,
    ApprovalRequest,
    HealthResponse,
    IncidentDetail,
    IncidentNoteRequest,
    IncidentSummary,
    MetricsResponse,
    ScenarioInjectionResponse,
)
from .serializers import incident_detail, incident_summary
from .services.incidents import (
    IncidentNotFoundError,
    IncidentService,
    InvalidIncidentStateError,
)
from .simulator import SimulatorClient, SimulatorError

settings = get_settings()
simulator = SimulatorClient(settings.simulator_base_url, timeout=settings.request_timeout_seconds)
investigator = build_investigator(settings)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "A supervised AI incident-response control plane with deterministic policy, "
        "approval-bound remediation, verification, and append-only Track history."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_origin, "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def service(db: Session = Depends(get_db)) -> IncidentService:
    return IncidentService(db, settings, simulator, investigator)


async def investigate_in_background(incident_id: str) -> None:
    with SessionLocal() as db:
        app_service = IncidentService(db, settings, simulator, investigator)
        await app_service.investigate(incident_id)


async def verify_in_background(incident_id: str) -> None:
    with SessionLocal() as db:
        app_service = IncidentService(db, settings, simulator, investigator)
        incident = app_service.get_incident(incident_id)
        if incident.status in {"verifying", "monitoring", "needs_evidence", "needs_human"}:
            await app_service.verify(incident_id)


def require_alertmanager_token(authorization: str | None) -> None:
    expected = f"Bearer {settings.alertmanager_webhook_token}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid monitoring webhook token")


def translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IncidentNotFoundError):
        return HTTPException(status_code=404, detail="Incident or action not found")
    if isinstance(exc, PolicyViolation):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, InvalidIncidentStateError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, SimulatorError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected control-plane error")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", agent_mode=settings.agent_mode, simulator_url=settings.simulator_base_url
    )


@app.get("/api/v1/scenarios", tags=["scenarios"])
async def scenarios(app_service: IncidentService = Depends(service)):
    try:
        return await app_service.list_scenarios()
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/scenarios/{scenario_key}/inject",
    response_model=ScenarioInjectionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["scenarios"],
)
async def inject_scenario(
    scenario_key: str, app_service: IncidentService = Depends(service)
) -> ScenarioInjectionResponse:
    try:
        activation = await app_service.inject_scenario(scenario_key)
        return ScenarioInjectionResponse.model_validate(activation)
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/scenarios/{scenario_key}/launch",
    response_model=IncidentDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["scenarios"],
    deprecated=True,
)
async def launch_scenario(
    scenario_key: str, app_service: IncidentService = Depends(service)
) -> IncidentDetail:
    try:
        return incident_detail(await app_service.launch_scenario(scenario_key))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/integrations/alertmanager",
    response_model=AlertmanagerIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["integrations"],
)
def receive_alertmanager_webhook(
    payload: AlertmanagerWebhook,
    background_tasks: BackgroundTasks,
    authorization: Annotated[str | None, Header()] = None,
    app_service: IncidentService = Depends(service),
) -> AlertmanagerIngestionResponse:
    require_alertmanager_token(authorization)
    try:
        result = app_service.ingest_alertmanager(payload)
        if settings.alertmanager_auto_investigate:
            for incident_id in result.created_incident_ids:
                background_tasks.add_task(investigate_in_background, incident_id)
            for incident_id in result.resolved_incident_ids:
                background_tasks.add_task(verify_in_background, incident_id)
        return result
    except Exception as exc:
        raise translate_error(exc) from exc


@app.get("/api/v1/incidents", response_model=list[IncidentSummary], tags=["incidents"])
def list_incidents(app_service: IncidentService = Depends(service)) -> list[IncidentSummary]:
    return [incident_summary(item) for item in app_service.list_incidents()]


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentDetail, tags=["incidents"])
def get_incident(
    incident_id: str, app_service: IncidentService = Depends(service)
) -> IncidentDetail:
    try:
        return incident_detail(app_service.get_incident(incident_id))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/incidents/{incident_id}/investigate",
    response_model=IncidentDetail,
    tags=["incidents"],
)
async def investigate(
    incident_id: str, app_service: IncidentService = Depends(service)
) -> IncidentDetail:
    try:
        return incident_detail(await app_service.investigate(incident_id))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/actions/{action_id}/approve",
    response_model=IncidentDetail,
    tags=["approvals"],
)
async def approve(
    action_id: str,
    payload: ApprovalRequest,
    app_service: IncidentService = Depends(service),
) -> IncidentDetail:
    try:
        return incident_detail(await app_service.approve_action(action_id, payload))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/actions/{action_id}/reject",
    response_model=IncidentDetail,
    tags=["approvals"],
)
def reject(
    action_id: str,
    payload: ApprovalRequest,
    app_service: IncidentService = Depends(service),
) -> IncidentDetail:
    try:
        return incident_detail(app_service.reject_action(action_id, payload))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/incidents/{incident_id}/verify",
    response_model=IncidentDetail,
    tags=["incidents"],
)
async def verify(
    incident_id: str, app_service: IncidentService = Depends(service)
) -> IncidentDetail:
    try:
        return incident_detail(await app_service.verify(incident_id))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.post(
    "/api/v1/incidents/{incident_id}/notes",
    response_model=IncidentDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["incidents"],
)
def add_incident_note(
    incident_id: str,
    payload: IncidentNoteRequest,
    app_service: IncidentService = Depends(service),
) -> IncidentDetail:
    try:
        return incident_detail(app_service.add_note(incident_id, payload))
    except Exception as exc:
        raise translate_error(exc) from exc


@app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["analytics"])
def metrics(app_service: IncidentService = Depends(service)) -> MetricsResponse:
    return app_service.metrics()
