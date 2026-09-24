package io.incidentcopilot.simulator.model;

public record DependencyStatus(
        String name,
        String status,
        int latencyMs,
        String message
) {
}
