# Login service — ambiguous failure increase

## Purpose

Use this runbook when several plausible causes exist and telemetry is incomplete.

## Investigation

1. Segment failures by identity provider.
2. Wait for delayed authentication logs.
3. Determine whether database latency is specific to session creation.
4. Compare failures with the recent application release.

## Response

Do not restart or roll back while evidence cannot distinguish the identity
provider, application release, and database hypotheses. Escalate or gather more
evidence. An explicit refusal to act is the expected safe result.

