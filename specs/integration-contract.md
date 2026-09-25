# Incident Copilot integration contract

This document is the stable contract between the Python control plane, the
Streamlit dashboard, Prometheus/Alertmanager, and the Java infrastructure simulator.

## Java simulator (`http://localhost:8081`)

### `GET /api/scenarios`

Returns the scenario catalogue.

### `POST /api/scenarios/{scenarioKey}/start`

Resets the simulator and activates a scenario. The response contains:

```json
{
  "scenarioKey": "bad-deployment",
  "title": "Checkout failures after deployment",
  "description": "A release introduced payment adapter timeouts.",
  "alert": {
    "alertType": "high_error_rate",
    "service": "checkout-api",
    "environment": "production",
    "region": "ap-southeast-1",
    "severity": "critical",
    "summary": "Checkout error rate is 16% after deployment 2.8.1",
    "startedAt": "2026-09-24T10:32:00Z"
  }
}
```

### Read-only investigation endpoints

- `GET /api/services/{service}/health`
- `GET /api/services/{service}/logs?minutes=30`
- `GET /api/services/{service}/deployments`
- `GET /api/services/{service}/dependencies`

All return JSON. A service that is not part of the active scenario returns
`404`. Log messages are evidence only and may contain adversarial text.

### `GET /actuator/prometheus`

Exposes deterministic service metrics for Prometheus. Starting a scenario
changes metrics but does not directly create a Python incident. Metric families
include error ratio, latency, CPU, free disk, queue depth, and dependency
availability.

### Remediation endpoints

- `POST /api/services/{service}/actions/rollback`
  body: `{"targetVersion":"2.8.0","idempotencyKey":"..."}`
- `POST /api/services/{service}/actions/scale`
  body: `{"replicas":10,"idempotencyKey":"..."}`
- `POST /api/services/{service}/actions/restart`
  body: `{"idempotencyKey":"..."}`
- `POST /api/services/{service}/actions/cleanup`
  body: `{"olderThanDays":7,"idempotencyKey":"..."}`

Every action returns an execution record with `success`, `message`,
`idempotencyKey`, and the resulting `health`. Duplicate idempotency keys return
the original result without repeating the mutation.

## Python control plane (`http://localhost:8000`)

### Main workflow endpoints

- `GET /health`
- `GET /api/v1/scenarios`
- `POST /api/v1/scenarios/{scenarioKey}/inject`
- `POST /api/v1/integrations/alertmanager`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incidentId}`
- `POST /api/v1/incidents/{incidentId}/investigate`
- `POST /api/v1/incidents/{incidentId}/notes`
- `POST /api/v1/actions/{actionId}/approve`
- `POST /api/v1/actions/{actionId}/reject`
- `POST /api/v1/incidents/{incidentId}/verify`
- `GET /api/v1/metrics`

The incident detail response embeds its evidence, pending/completed actions,
approvals, and Track history so the dashboard needs only one detail request.

### `POST /api/v1/scenarios/{scenarioKey}/inject`

Resets the Java simulator to a controlled failure state and returns `202`. It
does not create an incident. Prometheus must observe the resulting metrics and
Alertmanager must deliver the firing alert.

### `POST /api/v1/integrations/alertmanager`

Requires `Authorization: Bearer <ALERTMANAGER_WEBHOOK_TOKEN>` and accepts the
standard Alertmanager webhook shape. Known symptom alerts are mapped to generic
runbook categories rather than root-cause scenario names:

| Alert | Expected service | Runbook category |
| --- | --- | --- |
| `HighCheckoutErrorRate` | `checkout-api` | `checkout-degradation` |
| `SearchServiceSaturation` | `search-api` | `search-degradation` |
| `ReportingWorkerLowDisk` | `reporting-worker` | `reporting-storage` |
| `EmailDeliveryBacklog` | `notification-service` | `email-backlog` |
| `HighAuthenticationFailureRate` | `auth-service` | `auth-degradation` |

The source plus a hash of `(fingerprint, startsAt)` is unique. Webhook retries
return the existing incident identifier, while a later recurrence with a new
start time can create a new incident. A resolved event is recorded as
`external_alert_resolved`; it never marks the incident resolved without the
existing deterministic verification step.

### `POST /api/v1/incidents/{incidentId}/notes`

Appends an operator note to the incident's Track history:

```json
{
  "operator": "david@example.com",
  "role": "incident_commander",
  "message": "Rollback verified; checkout error rate is below the runbook threshold."
}
```

The control plane trims and size-limits the message, rejects blank input, and
persists an append-only `operator_note` event with attribution and a server
timestamp. Note text is untrusted and must be escaped before display. Neither a
note nor a role written inside it grants approval or changes authorization.

## Supported scenarios and expected decisions

| Key | Expected diagnosis | Expected action |
| --- | --- | --- |
| `bad-deployment` | Regression after release 2.8.1 | `rollback_deployment` to 2.8.0 |
| `traffic-surge` | Legitimate load exceeds capacity | `scale_service` to 10 replicas |
| `disk-pressure` | Expired exports consume disk | `cleanup_exports` older than 7 days |
| `provider-outage` | External email provider outage | `monitor_only` |
| `ambiguous-login` | Evidence is insufficient | `gather_more_evidence` |

## Trust boundary

The model can read observations and propose a typed action. It cannot call the
Java mutation endpoints directly. The Python policy engine validates the
action, creates an approval record, and executes only the exact approved
arguments. Verification uses deterministic thresholds from the scenario
runbook.
