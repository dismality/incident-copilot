# Notification service — external provider outage

## Purpose

Use this runbook when outbound email delivery fails but messages remain safely
queued.

## Investigation

1. Check the notification service and queue health.
2. Check the external provider's status.
3. Confirm messages are retained for retry.

## Response

Do not restart a healthy internal service during a confirmed provider outage.
Continue queueing, notify support, and monitor provider recovery. This scenario
intentionally has no internal remediation action.

## Recovery criteria

The incident remains in monitoring until the provider is healthy and queued
messages drain. The portfolio simulator does not fabricate provider recovery.

