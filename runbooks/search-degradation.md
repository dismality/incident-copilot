# Search API — saturation or high latency

Use this runbook when search latency and resource use are elevated. Determine
whether demand, a release, or a dependency explains the symptom.

## Investigation

1. Compare request volume with its recent baseline.
2. Inspect CPU, replica count, latency, deployments, and dependencies.
3. Scale only when traffic is legitimate, dependencies are healthy, and current
   capacity is the supported bottleneck.
4. If the cause is unclear, request more evidence rather than changing capacity.

## Recovery thresholds

- service status is `healthy`;
- CPU is below 70%; and
- p95 latency is below 800 ms.

Scaling requires human approval.
