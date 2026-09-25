# Checkout API — elevated errors or latency

Use this runbook when monitoring reports degraded checkout performance. The alert
describes a symptom and does not establish its cause.

## Investigation

1. Compare the alert start time with recent deployments.
2. Inspect application logs for a common failure signature.
3. Check the payment provider and database before blaming changed code.
4. Roll back only when the previous release was healthy and the evidence strongly
   correlates the degradation with the current release.
5. Otherwise gather more evidence; do not use a restart as a generic response.

## Recovery thresholds

- service status is `healthy`;
- error rate is below 2%; and
- p95 latency is below 700 ms.

Rollback is production-changing and always requires human approval.
