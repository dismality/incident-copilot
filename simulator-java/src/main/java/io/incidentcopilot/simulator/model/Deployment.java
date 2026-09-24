package io.incidentcopilot.simulator.model;

import java.time.Instant;

public record Deployment(
        String version,
        Instant deployedAt,
        String status,
        String commitSha
) {
}
