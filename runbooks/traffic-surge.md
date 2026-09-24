# Search API — legitimate traffic surge

## Purpose

Use this runbook when traffic, CPU, and latency rise together without a recent
release or dependency failure.

## Investigation

1. Confirm that request volume is genuinely elevated.
2. Check that authentication and traffic origin do not indicate abuse.
3. Verify database, cache, and search-index dependencies are healthy.
4. Confirm there was no relevant deployment near the alert time.

## Controlled remediation

Scale only within the policy limit of 1–20 replicas. Scaling production changes
cost and capacity and requires an authorized human.

## Recovery criteria

- service status is `healthy`;
- CPU is below 70%; and
- p95 latency is below 800 ms.

