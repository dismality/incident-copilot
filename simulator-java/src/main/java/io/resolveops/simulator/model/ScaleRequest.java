package io.resolveops.simulator.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ScaleRequest(
        @NotNull @Min(1) @Max(20) Integer replicas,
        @NotBlank @Size(max = 128) String idempotencyKey
) {
}
