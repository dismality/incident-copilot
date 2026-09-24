package io.incidentcopilot.simulator.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CleanupRequest(
        @NotNull @Min(1) @Max(365) Integer olderThanDays,
        @NotBlank @Size(max = 128) String idempotencyKey
) {
}
