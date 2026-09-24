# Incident Copilot integration contract

This document is the stable contract between the Python control plane, the
Streamlit dashboard, and the Java infrastructure simulator.

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
- `POST /api/v1/scenarios/{scenarioKey}/launch`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incidentId}`
- `POST /api/v1/incidents/{incidentId}/investigate`
- `POST /api/v1/actions/{actionId}/approve`
- `POST /api/v1/actions/{actionId}/reject`
- `POST /api/v1/incidents/{incidentId}/verify`
- `GET /api/v1/metrics`

The incident detail response embeds its evidence, pending/completed actions,
approvals, and audit timeline so the dashboard needs only one detail request.

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
