package io.resolveops.simulator.model;

import java.time.Instant;
import java.util.Map;

public record ServiceHealth(
        String service,
        String environment,
        String region,
        String status,
        boolean healthy,
        double errorRate,
        int latencyMs,
        double cpuPercent,
        int replicas,
        double diskFreePercent,
        String version,
        Instant observedAt,
        Map<String, Object> details
) {
    public ServiceHealth {
        details = details == null ? Map.of() : Map.copyOf(details);
    }
}
