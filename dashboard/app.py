"""Incident Copilot operator dashboard.

Run locally with:
    streamlit run app.py

The module is safe to import without a running API. Network access begins only
inside ``main`` and every request is presented as a recoverable UI state.
"""

from __future__ import annotations

import html
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

import streamlit as st

from api_client import ControlPlaneError, IncidentCopilotClient
from styles import inject_styles

T = TypeVar("T")

DEFAULT_API_URL = os.getenv("INCIDENT_COPILOT_API_URL", "http://localhost:8000")

SCENARIO_CATALOGUE: list[dict[str, str]] = [
    {
        "scenarioKey": "bad-deployment",
        "title": "Checkout regression",
        "description": "A new release introduces payment-adapter timeouts and a sharp error-rate increase.",
        "decision": "Rollback 2.8.1 → 2.8.0",
        "icon": "↶",
    },
    {
        "scenarioKey": "traffic-surge",
        "title": "Capacity saturation",
        "description": "Legitimate demand pushes search CPU and latency beyond the operating threshold.",
        "decision": "Scale to 10 replicas",
        "icon": "↗",
    },
    {
        "scenarioKey": "disk-pressure",
        "title": "Disk pressure",
        "description": "Expired exports consume a worker's disk while protected application data remains healthy.",
        "decision": "Clean exports older than 7 days",
        "icon": "◫",
    },
    {
        "scenarioKey": "provider-outage",
        "title": "Provider outage",
        "description": "A third-party email provider is unavailable while internal services remain healthy.",
        "decision": "Monitor only — no mutation",
        "icon": "⌁",
    },
    {
        "scenarioKey": "ambiguous-login",
        "title": "Ambiguous login failures",
        "description": "Conflicting evidence makes remediation unsafe until further investigation is completed.",
        "decision": "Gather more evidence",
        "icon": "?",
    },
]

ROLE_OPTIONS = {
    "Incident commander": "incident_commander",
    "Platform engineer": "platform_engineer",
    "Read-only analyst": "read_only_analyst",
}


def main() -> None:
    st.set_page_config(
        page_title="Incident Copilot | Incident Command",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    _initialize_state()

    api_url, operator, role = _sidebar()
    client = IncidentCopilotClient(api_url)

    _render_header()
    _render_flash()

    health, health_error = _attempt(client.health)
    connected = health_error is None
    _render_connection_strip(connected, api_url, health, health_error)

    if connected:
        scenarios, _ = _attempt(client.scenarios)
        incidents, incident_error = _attempt(client.incidents)
        metrics, metrics_error = _attempt(client.metrics)
        scenarios = _merge_scenarios(scenarios or [])
        incidents = incidents or []
        metrics = metrics or {}
    else:
        scenarios = SCENARIO_CATALOGUE
        incidents = []
        metrics = {}
        incident_error = metrics_error = health_error

    _render_metric_ribbon(metrics, incidents, connected)
    _render_scenarios(client, scenarios, connected)

    st.markdown(
        '<div class="ops-section-heading"><div><h2>Incident command</h2>'
        "<p>Investigate, authorize, execute and verify from one controlled workspace.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    queue_column, detail_column = st.columns([0.34, 0.66], gap="large")
    with queue_column:
        _render_incident_queue(incidents, incident_error)

    with detail_column:
        selected_id = st.session_state.get("selected_incident_id")
        if not selected_id and incidents:
            selected_id = _incident_id(incidents[0])
            st.session_state.selected_incident_id = selected_id

        if selected_id and connected:
            detail, detail_error = _attempt(lambda: client.incident(str(selected_id)))
            if detail_error:
                _render_error_state(
                    "Incident unavailable",
                    _error_copy(detail_error),
                    icon="!",
                )
            elif detail:
                _render_incident_detail(client, detail, operator, role)
            else:
                _render_empty_state(
                    "Incident not found",
                    "Select another incident or refresh the queue.",
                    "⌁",
                )
        else:
            _render_empty_state(
                "No incident selected",
                "Launch a scenario above. The alert, evidence and supervised resolution workflow will appear here.",
                "◇",
            )

    _render_portfolio_metrics(metrics, metrics_error, connected)
    _render_footer()


def _initialize_state() -> None:
    defaults = {
        "selected_incident_id": None,
        "operator_identity": "david@example.com",
        "operator_role_label": "Incident commander",
        "api_url": DEFAULT_API_URL,
        "status_filter": "All states",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.markdown(
            '<div class="ops-wordmark">INCIDENT<span>//</span>COPILOT</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ops-kicker">Operator console</div>', unsafe_allow_html=True
        )
        st.caption("A supervised AI workspace for simulated infrastructure incidents.")

        st.markdown("### Session")
        operator = st.text_input(
            "Operator identity",
            key="operator_identity",
            help="Recorded on every approval or rejection.",
        ).strip()
        role_label = st.selectbox(
            "Active role",
            list(ROLE_OPTIONS),
            key="operator_role_label",
        )
        role = ROLE_OPTIONS[role_label]

        st.markdown("### Control plane")
        api_url = (
            st.text_input(
                "Base URL",
                key="api_url",
                help="Python FastAPI control-plane address.",
            )
            .strip()
            .rstrip("/")
        )

        if st.button("Refresh workspace", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.markdown(
            '<div class="simulation-note"><b>Simulation boundary</b><br>'
            "All actions target the Java infrastructure simulator. The model cannot "
            "call mutation endpoints directly.</div>",
            unsafe_allow_html=True,
        )
    return api_url or DEFAULT_API_URL, operator, role


def _render_header() -> None:
    left, right = st.columns([0.79, 0.21], vertical_alignment="bottom")
    with left:
        st.markdown(
            '<div class="ops-kicker">AI incident response copilot</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ops-title">Clarity under pressure.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ops-subtitle">Evidence-led investigation, policy-controlled execution '
            "and deterministic recovery verification—designed for humans to remain in command.</div>",
            unsafe_allow_html=True,
        )
    with right:
        now = datetime.now(UTC).strftime("%d %b %Y · %H:%M UTC")
        st.markdown(
            f'<div class="ops-panel"><div class="ops-label">Command clock</div>'
            f'<div style="font-family:ui-monospace,monospace;color:#d9e7f5;margin-top:.35rem;font-size:.82rem">{now}</div></div>',
            unsafe_allow_html=True,
        )


def _render_connection_strip(
    connected: bool,
    api_url: str,
    health: dict[str, Any] | None,
    error: ControlPlaneError | None,
) -> None:
    if connected:
        health_status = str((health or {}).get("status", "operational")).replace(
            "_", " "
        )
        st.markdown(
            f'<div style="margin:1.15rem 0 .25rem">{_badge("Control plane " + health_status, "success", dot=True)} '
            f"{_badge('Supervised execution', 'info')} {_badge('Simulation', 'purple')}</div>",
            unsafe_allow_html=True,
        )
    else:
        detail = _error_copy(error)
        st.markdown(
            f'<div class="offline-state"><b>Control plane offline.</b> {html.escape(detail)}<br>'
            f'<span style="color:#aebed0">Expected at {html.escape(api_url)}. The workspace remains safe and read-only until it reconnects.</span></div>',
            unsafe_allow_html=True,
        )


def _render_metric_ribbon(
    metrics: dict[str, Any], incidents: list[dict[str, Any]], connected: bool
) -> None:
    total = metrics.get("totalIncidents", len(incidents) if connected else None)
    resolved = metrics.get(
        "resolvedIncidents",
        sum(_norm(item.get("status")) == "resolved" for item in incidents)
        if connected
        else None,
    )
    pending = metrics.get(
        "pendingApprovals",
        sum(_has_pending_approval(item) for item in incidents) if connected else None,
    )
    time_saved = metrics.get("simulatedTimeSavedPercent")

    columns = st.columns(4, gap="small")
    values = [
        ("Total incidents", _display_number(total), "Simulation cases"),
        ("Resolved", _display_number(resolved), "Recovery verified"),
        ("Pending approval", _display_number(pending), "Human decisions"),
        ("Time saved", _percent(time_saved), "Simulated baseline"),
    ]
    for column, (label, value, help_text) in zip(columns, values, strict=True):
        column.metric(label, value, help=help_text)


def _render_scenarios(
    client: IncidentCopilotClient,
    scenarios: list[dict[str, Any]],
    connected: bool,
) -> None:
    st.markdown(
        '<div class="ops-section-heading"><div><h2>Scenario lab</h2>'
        "<p>Launch a deterministic failure state and observe how the copilot responds.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    if not scenarios:
        _render_empty_state(
            "No scenarios available",
            "The simulator did not return a scenario catalogue.",
            "□",
        )
        return

    columns = st.columns(min(5, len(scenarios)), gap="small")
    for index, scenario in enumerate(scenarios):
        key = str(scenario.get("scenarioKey") or scenario.get("key") or "")
        title = str(scenario.get("title") or key.replace("-", " ").title())
        description = str(
            scenario.get("description") or "Controlled incident simulation."
        )
        icon = str(scenario.get("icon") or "◇")
        decision = str(scenario.get("decision") or "Evidence-led decision")
        with columns[index % len(columns)], st.container(border=True):
            st.markdown(
                f'<div class="scenario-icon">{html.escape(icon)}</div>'
                f'<div class="scenario-title">{html.escape(title)}</div>'
                f'<div class="scenario-detail">{html.escape(description)}</div>'
                f'<div style="margin:.55rem 0">{_badge(decision, "info")}</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Launch scenario",
                key=f"launch_{key}",
                use_container_width=True,
                disabled=not connected or not key,
            ):
                _launch(client, key, title)


def _launch(client: IncidentCopilotClient, scenario_key: str, title: str) -> None:
    with st.spinner(f"Activating {title}…"):
        incident, error = _attempt(lambda: client.launch_scenario(scenario_key))
    if error:
        st.error(_error_copy(error))
        return
    incident_id = _incident_id(incident or {})
    if incident_id:
        st.session_state.selected_incident_id = incident_id
    _set_flash("success", f"Scenario launched: {title}")
    st.rerun()


def _render_incident_queue(
    incidents: list[dict[str, Any]], error: ControlPlaneError | None
) -> None:
    heading_left, heading_right = st.columns([0.7, 0.3], vertical_alignment="center")
    heading_left.markdown("#### Incident queue")
    heading_right.caption(f"{len(incidents)} total")

    if error:
        _render_error_state("Queue unavailable", _error_copy(error), "!")
        return

    statuses = sorted(
        {_pretty(item.get("status")) for item in incidents if item.get("status")}
    )
    status_filter = st.selectbox(
        "Filter incidents",
        ["All states", *statuses],
        key="status_filter",
        label_visibility="collapsed",
    )
    visible = incidents
    if status_filter != "All states":
        visible = [
            item for item in incidents if _pretty(item.get("status")) == status_filter
        ]

    if not visible:
        _render_empty_state(
            "Queue is clear",
            "Launch a scenario to open an incident, or change the status filter.",
            "✓",
        )
        return

    selected = str(st.session_state.get("selected_incident_id") or "")
    for incident in visible:
        incident_id = _incident_id(incident)
        status = str(incident.get("status", "open"))
        severity = str(incident.get("severity", "unknown"))
        title = str(
            incident.get("title") or incident.get("alertSummary") or "Untitled incident"
        )
        service = str(incident.get("service") or "Unknown service")
        created = _format_time(incident.get("createdAt"), compact=True)
        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;gap:.5rem">'
                f'<span class="incident-id">{html.escape(_short_id(incident_id))}</span>'
                f"{_badge(_pretty(severity), _severity_tone(severity))}</div>"
                f'<div style="font-weight:700;color:#edf5ff;font-size:.9rem;margin:.5rem 0 .2rem">{html.escape(title)}</div>'
                f'<div class="ops-muted">{html.escape(service)} · {html.escape(created)}</div>'
                f'<div style="margin-top:.55rem">{_badge(_pretty(status), _status_tone(status), dot=True)}</div>',
                unsafe_allow_html=True,
            )
            button_label = (
                "Viewing incident" if incident_id == selected else "Open incident"
            )
            if st.button(
                button_label,
                key=f"select_{incident_id}",
                use_container_width=True,
                disabled=incident_id == selected,
            ):
                st.session_state.selected_incident_id = incident_id
                st.rerun()


def _render_incident_detail(
    client: IncidentCopilotClient,
    incident: dict[str, Any],
    operator: str,
    role: str,
) -> None:
    incident_id = _incident_id(incident)
    title = str(
        incident.get("title") or incident.get("alertSummary") or "Untitled incident"
    )
    status = str(incident.get("status", "open"))
    severity = str(incident.get("severity", "unknown"))
    recovery_verified = bool(incident.get("recoveryVerified"))

    st.markdown(
        f'<div class="ops-panel accent"><div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap">'
        f'<div><div class="incident-id">INCIDENT · {html.escape(incident_id)}</div>'
        f'<div class="incident-title">{html.escape(title)}</div>'
        f'<div class="ops-muted">{html.escape(str(incident.get("service") or "Unknown service"))} '
        f"· {html.escape(str(incident.get('environment') or 'unknown'))} "
        f"· {html.escape(str(incident.get('region') or 'global'))}</div></div>"
        f"<div>{_badge(_pretty(severity), _severity_tone(severity))} "
        f"{_badge(_pretty(status), _status_tone(status), dot=True)}</div></div></div>",
        unsafe_allow_html=True,
    )

    if incident.get("alertSummary"):
        st.caption(f"Alert · {incident['alertSummary']}")

    action_left, action_mid, action_right = st.columns([0.38, 0.31, 0.31])
    can_investigate = _norm(status) in {
        "new",
        "needs_evidence",
        "needs_human",
        "monitoring",
    }
    if action_left.button(
        "Run AI investigation",
        type="primary",
        use_container_width=True,
        disabled=not can_investigate,
        key=f"investigate_{incident_id}",
    ):
        _call_and_refresh(
            lambda: client.investigate(incident_id),
            "Investigation complete. Evidence and recommendation updated.",
        )
    if action_mid.button(
        "Verify recovery",
        use_container_width=True,
        key=f"verify_{incident_id}",
        disabled=not _can_verify(incident),
    ):
        _call_and_refresh(
            lambda: client.verify(incident_id),
            "Recovery verification completed.",
        )
    action_right.markdown(
        f'<div style="padding:.4rem 0;text-align:right">'
        f"{_badge('Recovery verified', 'success', dot=True) if recovery_verified else _badge('Verification pending', 'warning')}"
        "</div>",
        unsafe_allow_html=True,
    )

    _render_diagnosis(incident)
    evidence_tab, actions_tab, audit_tab = st.tabs(
        ["Evidence", "Actions & approvals", "Audit timeline"]
    )
    with evidence_tab:
        _render_evidence(
            incident.get("evidence") or [], incident.get("missingInformation") or []
        )
    with actions_tab:
        _render_actions(client, incident, operator, role)
    with audit_tab:
        _render_timeline(incident.get("timeline") or [])


def _render_diagnosis(incident: dict[str, Any]) -> None:
    cause = incident.get("likelyCause")
    summary = incident.get("summary")
    confidence = incident.get("confidence")
    if cause or summary:
        left, right = st.columns([0.8, 0.2])
        with left:
            st.markdown(
                f'<div class="cause-box"><div class="ops-label">Current hypothesis</div>'
                f'<div class="cause">{html.escape(str(cause or "No supported root cause yet"))}</div>'
                f'<div class="summary">{html.escape(str(summary or ""))}</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            st.metric(
                "Confidence",
                _confidence(confidence),
                help="Model-reported confidence; evidence remains authoritative.",
            )
    else:
        st.markdown(
            '<div class="cause-box"><div class="ops-label">Current hypothesis</div>'
            '<div class="cause">Investigation not started</div>'
            '<div class="summary">Run the AI investigation to gather evidence and propose a policy-checked response.</div></div>',
            unsafe_allow_html=True,
        )


def _render_evidence(evidence: list[dict[str, Any]], missing: list[Any]) -> None:
    if missing:
        with st.expander(
            f"Missing information · {len(missing)} item(s)", expanded=True
        ):
            for item in missing:
                st.markdown(f"- {item}")

    if not evidence:
        _render_empty_state(
            "No evidence collected",
            "Run the investigation to query health, logs, deployments, dependencies and the relevant runbook.",
            "⌕",
        )
        return

    for index, item in enumerate(evidence):
        source = _pretty(item.get("source") or "observation")
        title = str(item.get("title") or f"Evidence {index + 1}")
        detail = str(
            item.get("detail") or item.get("observation") or "No detail returned"
        )
        created = _format_time(item.get("createdAt"))
        with st.container(border=True):
            head, time_column = st.columns([0.75, 0.25])
            head.markdown(
                f'<div style="font-weight:700;color:#edf5ff">{html.escape(title)}</div>'
                f'<div class="ops-muted">{html.escape(source)}</div>',
                unsafe_allow_html=True,
            )
            time_column.caption(created)
            st.markdown(
                f'<div class="evidence-detail">{html.escape(detail)}</div>',
                unsafe_allow_html=True,
            )


def _render_actions(
    client: IncidentCopilotClient,
    incident: dict[str, Any],
    operator: str,
    role: str,
) -> None:
    actions = incident.get("actions") or []
    approvals = incident.get("approvals") or []
    if not actions:
        _render_empty_state(
            "No action proposed",
            "The copilot may recommend a controlled remediation, monitoring only, or additional evidence.",
            "◇",
        )
        return

    for action in actions:
        action_id = str(action.get("id") or "")
        tool = str(action.get("toolName") or "unknown_action")
        status = str(action.get("status") or "proposed")
        risk = str(action.get("riskLevel") or "unknown")
        reason = str(action.get("reason") or "No rationale returned.")
        expected = str(action.get("expectedResult") or "No expected result provided.")
        args = action.get("arguments") or {}

        with st.container(border=True):
            title_col, badge_col = st.columns([0.68, 0.32])
            title_col.markdown(f"#### `{tool}`")
            badge_col.markdown(
                f'<div style="text-align:right">{_badge(_pretty(risk) + " risk", _risk_tone(risk))} '
                f"{_badge(_pretty(status), _status_tone(status), dot=True)}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(reason)
            arg_col, result_col = st.columns(2)
            with arg_col:
                st.caption("Exact proposed arguments")
                st.code(json.dumps(args, indent=2, default=str), language="json")
            with result_col:
                st.caption("Expected result")
                st.markdown(expected)
                if action.get("executionResult") is not None:
                    with st.expander("Execution result"):
                        st.json(action["executionResult"])

            if _action_requires_decision(status):
                _render_decision_controls(client, action_id, operator, role)
            elif action.get("approvedBy"):
                st.success(f"Approved by {action['approvedBy']}")

    if approvals:
        with st.expander(f"Decision history · {len(approvals)}"):
            for approval in reversed(approvals):
                decision = _pretty(approval.get("decision") or "recorded")
                st.markdown(
                    f'<div style="color:#edf5ff;font-weight:700">{html.escape(decision)}</div>'
                    f'<div class="ops-muted">by {html.escape(str(approval.get("operator", "unknown")))} '
                    f"as {html.escape(_pretty(approval.get('role')))}</div>"
                    f'<div class="evidence-detail" style="margin-top:.35rem">'
                    f"{html.escape(str(approval.get('comment') or 'No comment supplied'))}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(_format_time(approval.get("createdAt")))
                st.divider()


def _render_decision_controls(
    client: IncidentCopilotClient,
    action_id: str,
    operator: str,
    role: str,
) -> None:
    st.markdown("##### Human authorization required")
    role_authorized = role in {"incident_commander", "platform_engineer"}
    if not operator:
        st.warning(
            "Enter an operator identity in the sidebar before making a decision."
        )
    if not role_authorized:
        st.info(
            "The active role is read-only. Switch to an authorized role to approve or reject this action."
        )
    comment_key = f"comment_{action_id}"
    comment = st.text_area(
        "Decision comment",
        key=comment_key,
        placeholder="State the evidence or concern behind this decision…",
        height=85,
    ).strip()
    approve_col, reject_col = st.columns(2)
    approve_disabled = not operator or not comment or not role_authorized
    if approve_col.button(
        "Approve exact action",
        type="primary",
        use_container_width=True,
        key=f"approve_{action_id}",
        disabled=approve_disabled,
    ):
        _call_and_refresh(
            lambda: client.approve_action(
                action_id, operator=operator, role=role, comment=comment
            ),
            "Action approved, executed and recorded.",
        )
    if reject_col.button(
        "Reject action",
        use_container_width=True,
        key=f"reject_{action_id}",
        disabled=approve_disabled,
    ):
        _call_and_refresh(
            lambda: client.reject_action(
                action_id, operator=operator, role=role, comment=comment
            ),
            "Action rejected. No mutation was performed.",
        )
    st.caption(
        "Approval is bound to the displayed tool and exact arguments. A changed proposal requires a new decision."
    )


def _render_timeline(timeline: list[dict[str, Any]]) -> None:
    if not timeline:
        _render_empty_state(
            "No audit events",
            "Every alert, tool call, policy decision, approval and verification will be recorded here.",
            "⋮",
        )
        return

    items: list[str] = []
    for event in timeline:
        event_type = _pretty(event.get("eventType") or "event")
        message = str(event.get("message") or event_type)
        actor = str(event.get("actor") or "system")
        created = _format_time(event.get("createdAt"))
        items.append(
            '<div class="timeline-item">'
            f'<div class="timeline-time">{html.escape(created)} · {html.escape(event_type.upper())}</div>'
            f'<div class="timeline-message">{html.escape(message)}</div>'
            f'<div class="timeline-actor">Actor · {html.escape(actor)}</div>'
            "</div>"
        )
    st.markdown(
        '<div class="timeline">' + "".join(items) + "</div>", unsafe_allow_html=True
    )

    detailed = [event for event in timeline if event.get("details")]
    if detailed:
        with st.expander("Technical event details"):
            for event in reversed(detailed):
                st.caption(
                    f"{_format_time(event.get('createdAt'))} · {_pretty(event.get('eventType'))}"
                )
                st.json(event.get("details"))


def _render_portfolio_metrics(
    metrics: dict[str, Any],
    error: ControlPlaneError | None,
    connected: bool,
) -> None:
    st.markdown(
        '<div class="ops-section-heading"><div><h2>Operational outcomes</h2>'
        "<p>Measured portfolio signals from completed simulation runs.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if error and connected:
        _render_error_state("Metrics unavailable", _error_copy(error), "↯")
        return

    total = metrics.get("totalIncidents")
    resolved = metrics.get("resolvedIncidents")
    resolution_rate = None
    try:
        if float(total) > 0:
            resolution_rate = float(resolved or 0) / float(total) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    columns = st.columns(4, gap="small")
    values = [
        (
            "Verified resolution rate",
            _percent(resolution_rate),
            "Resolved incidents / total incidents",
        ),
        (
            "Approval rate",
            _ratio_percent(metrics.get("approvalRate")),
            "Approved / completed human decisions",
        ),
        (
            "Median recommendation",
            _seconds(metrics.get("medianRecommendationSeconds")),
            "Alert to proposed action",
        ),
        (
            "Simulated time saved",
            _percent(metrics.get("simulatedTimeSavedPercent")),
            "Against the manual investigation baseline",
        ),
    ]
    for column, (label, value, help_text) in zip(columns, values, strict=True):
        column.metric(label, value, help=help_text)

    st.caption(
        "Metrics are calculated from controlled simulations. They demonstrate system behavior and must not be presented as production outcomes."
    )


def _render_footer() -> None:
    st.markdown("---")
    left, right = st.columns([0.72, 0.28])
    left.caption(
        "Incident Copilot · AI proposes · Policy constrains · Humans authorize · Code verifies"
    )
    right.caption("Portfolio simulation · No production access")


def _attempt(call: Callable[[], T]) -> tuple[T | None, ControlPlaneError | None]:
    try:
        return call(), None
    except ControlPlaneError as exc:
        return None, exc
    except Exception as exc:  # noqa: BLE001 - keep the UI recoverable on malformed data.
        return None, ControlPlaneError(
            "The dashboard could not process the control-plane response.",
            endpoint="dashboard",
            detail=str(exc),
        )


def _call_and_refresh(call: Callable[[], Any], success_message: str) -> None:
    with st.spinner("Applying controlled workflow…"):
        _, error = _attempt(call)
    if error:
        st.error(_error_copy(error))
        return
    _set_flash("success", success_message)
    st.rerun()


def _set_flash(level: str, message: str) -> None:
    st.session_state["flash"] = {"level": level, "message": message}


def _render_flash() -> None:
    flash = st.session_state.pop("flash", None)
    if not flash:
        return
    renderer = getattr(st, flash.get("level", "info"), st.info)
    renderer(flash.get("message", "Workspace updated."))


def _render_empty_state(title: str, copy: str, icon: str) -> None:
    st.markdown(
        f'<div class="empty-state"><div class="icon">{html.escape(icon)}</div>'
        f'<div class="title">{html.escape(title)}</div>'
        f'<div class="copy">{html.escape(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def _render_error_state(title: str, copy: str, icon: str) -> None:
    st.markdown(
        f'<div class="empty-state" style="border-color:rgba(255,107,122,.35)">'
        f'<div class="icon" style="color:#ff6b7a">{html.escape(icon)}</div>'
        f'<div class="title">{html.escape(title)}</div>'
        f'<div class="copy">{html.escape(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def _merge_scenarios(remote: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not remote:
        return SCENARIO_CATALOGUE
    local_by_key = {item["scenarioKey"]: item for item in SCENARIO_CATALOGUE}
    merged: list[dict[str, Any]] = []
    for item in remote:
        key = str(item.get("scenarioKey") or item.get("key") or "")
        merged.append({**local_by_key.get(key, {}), **item, "scenarioKey": key})
    return merged


def _incident_id(incident: dict[str, Any]) -> str:
    return str(incident.get("id") or incident.get("incidentId") or "")


def _has_pending_approval(incident: dict[str, Any]) -> bool:
    actions = incident.get("actions") or []
    return any(
        _action_requires_decision(str(action.get("status"))) for action in actions
    )


def _action_requires_decision(status: str) -> bool:
    return _norm(status) in {
        "proposed",
        "pending",
        "pending_approval",
        "awaiting_approval",
        "approval_required",
    }


def _can_verify(incident: dict[str, Any]) -> bool:
    if incident.get("recoveryVerified"):
        return False
    if _norm(incident.get("status")) in {
        "verifying",
        "monitoring",
        "needs_evidence",
        "needs_human",
    }:
        return True
    actions = incident.get("actions") or []
    return any(
        _norm(action.get("status"))
        in {"executed", "completed", "approved", "succeeded", "success"}
        for action in actions
    )


def _badge(label: str, tone: str = "info", dot: bool = False) -> str:
    safe_label = html.escape(label)
    marker = '<span class="ops-dot"></span>' if dot else ""
    return f'<span class="ops-badge {tone}">{marker}{safe_label}</span>'


def _severity_tone(value: Any) -> str:
    normalized = _norm(value)
    if normalized in {"critical", "sev1", "high"}:
        return "danger"
    if normalized in {"warning", "medium", "sev2"}:
        return "warning"
    return "info"


def _status_tone(value: Any) -> str:
    normalized = _norm(value)
    if normalized in {
        "resolved",
        "closed",
        "verified",
        "executed",
        "completed",
        "approved",
        "success",
        "succeeded",
    }:
        return "success"
    if normalized in {"failed", "rejected", "blocked", "critical"}:
        return "danger"
    if normalized in {
        "pending",
        "pending_approval",
        "awaiting_approval",
        "approval_required",
        "investigating",
        "open",
    }:
        return "warning"
    return "info"


def _risk_tone(value: Any) -> str:
    normalized = _norm(value)
    if normalized in {"high", "critical", "prohibited"}:
        return "danger"
    if normalized in {"medium", "moderate"}:
        return "warning"
    return "success"


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", " ").replace(" ", "_")


def _pretty(value: Any) -> str:
    text = str(value or "Unknown").replace("_", " ").replace("-", " ")
    return " ".join(text.split()).title()


def _short_id(value: str) -> str:
    if len(value) <= 15:
        return value
    return f"{value[:8]}…{value[-4:]}"


def _format_time(value: Any, compact: bool = False) -> str:
    if not value:
        return "Time unavailable"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if compact:
            return parsed.strftime("%d %b · %H:%M")
        return parsed.strftime("%d %b %Y · %H:%M:%S UTC")
    except ValueError:
        return text


def _display_number(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _percent(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
        if 0 <= number <= 1 and number not in {0, 1}:
            number *= 100
        return f"{number:.0f}%"
    except (TypeError, ValueError):
        return str(value)


def _ratio_percent(value: Any) -> str:
    """Format a known zero-to-one ratio as a percentage."""

    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return str(value)


def _seconds(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return str(value)


def _confidence(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
        if 0 <= number <= 1:
            number *= 100
        return f"{number:.0f}%"
    except (TypeError, ValueError):
        return str(value)


def _error_copy(error: ControlPlaneError | None) -> str:
    if error is None:
        return "An unknown error occurred."
    if error.detail:
        return f"{error.message} {error.detail}"
    return error.message


if __name__ == "__main__":
    main()
