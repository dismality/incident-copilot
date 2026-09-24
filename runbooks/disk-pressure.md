# Reporting worker — disk pressure

## Purpose

Use this runbook when a reporting worker has less than 5% free disk space.

## Investigation

1. Identify which approved directory is consuming space.
2. Confirm the files are temporary exports rather than application, database, or
   customer-uploaded data.
3. Compare file age with the seven-day retention policy.

## Controlled remediation

The only permitted cleanup removes expired files from the simulator's temporary
export directory. Arbitrary paths and arbitrary shell commands are prohibited.
Cleanup is destructive and requires approval.

## Recovery criteria

- free disk space is at least 25%; and
- the reporting worker is `healthy`.

