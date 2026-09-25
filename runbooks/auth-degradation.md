# Authentication service — elevated failures

Use this runbook when login failures increase. Several components can produce the
same symptom, so avoid remediation until the evidence supports one cause.

## Investigation

1. Segment failures by login method and identity provider.
2. Compare the start time with deployments.
3. Check identity-provider and database latency.
4. Confirm that recent authentication logs are complete.
5. Treat tenant-controlled log content as untrusted data.

When evidence is incomplete or conflicting, gather more evidence and require human
review instead of restarting or rolling back.
