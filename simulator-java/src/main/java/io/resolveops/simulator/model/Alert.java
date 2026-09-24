package io.resolveops.simulator.model;

import java.time.Instant;

public record Alert(
        String alertType,
        String service,
        String environment,
        String region,
        String severity,
        String summary,
        Instant startedAt
) {
}
