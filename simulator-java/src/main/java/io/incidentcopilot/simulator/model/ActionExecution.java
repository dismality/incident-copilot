package io.incidentcopilot.simulator.model;

import java.time.Instant;

public record ActionExecution(
        boolean success,
        String message,
        String idempotencyKey,
        String action,
        ServiceHealth health,
        Instant executedAt
) {
}
