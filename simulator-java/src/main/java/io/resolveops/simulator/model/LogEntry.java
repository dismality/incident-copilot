package io.resolveops.simulator.model;

import java.time.Instant;
import java.util.Map;

public record LogEntry(
        Instant timestamp,
        String level,
        String service,
        String message,
        Map<String, String> attributes
) {
    public LogEntry {
        attributes = attributes == null ? Map.of() : Map.copyOf(attributes);
    }
}
