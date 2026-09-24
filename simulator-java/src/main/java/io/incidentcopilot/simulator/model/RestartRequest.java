package io.incidentcopilot.simulator.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RestartRequest(
        @NotBlank @Size(max = 128) String idempotencyKey
) {
}
