# Checkout API — elevated errors after deployment

## Purpose

Use this runbook when checkout failures rise shortly after an application release.

## Investigation

1. Compare the alert start time with recent deployments.
2. Search for errors in components modified by the latest release.
3. Check payment-provider and database health before blaming a dependency.
4. Prefer a rollback only when the previous release was healthy and the timing and
   error signature support a regression.

## Controlled remediation

`rollback_deployment` is a production-changing operation and always requires an
authorized human. The exact service, environment, and target version shown to
the reviewer must match the execution arguments.

## Recovery criteria

- service status is `healthy`;
- error rate remains below 2%; and
- p95 latency remains below 700 ms.

Tool success alone is not recovery.

