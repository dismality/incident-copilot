# ResolveOps infrastructure simulator

This Spring Boot service provides deterministic infrastructure incidents for the
ResolveOps Python control plane. It contains no real cloud credentials and never
touches real infrastructure. Starting a scenario resets all in-memory state.

## Run locally

Requires Java 21 and Maven 3.9 or newer:

```bash
mvn spring-boot:run
```

Or build and run the self-contained image:

```bash
docker build -t resolveops-simulator .
docker run --rm -p 8081:8081 resolveops-simulator
```

The API is available at `http://localhost:8081`; Spring Boot health is exposed at
`http://localhost:8081/actuator/health`.

## Typical workflow

```bash
curl -X POST http://localhost:8081/api/scenarios/bad-deployment/start
curl http://localhost:8081/api/services/checkout-api/health
curl http://localhost:8081/api/services/checkout-api/logs?minutes=30
curl http://localhost:8081/api/services/checkout-api/deployments
curl http://localhost:8081/api/services/checkout-api/dependencies
curl -X POST http://localhost:8081/api/services/checkout-api/actions/rollback \
  -H "Content-Type: application/json" \
  -d '{"targetVersion":"2.8.0","idempotencyKey":"incident-1-action-1"}'
```

Every remediation returns its resulting health snapshot. Reusing an idempotency
key returns the original execution record without applying another mutation.

## Scenarios

| Key | Service | Intended outcome |
| --- | --- | --- |
| `bad-deployment` | `checkout-api` | Roll back from 2.8.1 to 2.8.0 |
| `traffic-surge` | `search-api` | Scale to 10 replicas |
| `disk-pressure` | `reporting-worker` | Remove exports older than 7 days |
| `provider-outage` | `notification-service` | Monitor; internal changes do not fix it |
| `ambiguous-login` | `auth-service` | Gather more evidence; do not guess |

Run all unit and HTTP-contract tests with:

```bash
mvn verify
```
