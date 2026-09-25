# Notification service — email delivery backlog

Use this runbook when queued email deliveries increase or delivery failures are
reported. Determine whether the internal service or an external provider is at
fault.

## Investigation

1. Check notification-service process health and durable queue state.
2. Inspect recent deployments and application logs.
3. Check the email provider independently.
4. Do not restart a healthy internal service during a confirmed provider outage.
5. Preserve queued messages and monitor until the dependency recovers.

An external alert returning to normal is not proof of recovery; verify the service
and queue independently.
