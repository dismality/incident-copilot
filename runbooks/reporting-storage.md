# Reporting worker — low available storage

Use this runbook when monitoring reports low disk space or failed report writes.

## Investigation

1. Identify which directory is consuming storage.
2. Separate temporary exports from protected application and database data.
3. Confirm the configured export-retention policy.
4. Cleanup is allowed only for expired files in the temporary export directory.

## Recovery thresholds

- service status is `healthy`; and
- free disk space is at least 25%.

Cleanup is destructive and always requires human approval.
