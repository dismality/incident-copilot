# Contributing

Incident Copilot is a portfolio reference project built around a strict trust
boundary: model output is a proposal, never authorization.

1. Create a focused branch.
2. Add or update tests for every behavior change.
3. Run Python lint/tests and `mvn verify` for Java changes.
4. Never add real customer logs, credentials, or infrastructure endpoints.
5. Keep all remediation tools narrow, typed, idempotent, and policy checked.

Security-sensitive changes should also update `docs/threat-model.md` and the
relevant adversarial cases in `docs/evaluation-plan.md`.
