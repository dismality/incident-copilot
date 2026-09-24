package io.resolveops.simulator.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RollbackRequest(
        @NotBlank @Size(max = 80)
        @Pattern(regexp = "[A-Za-z0-9][A-Za-z0-9._-]*", message = "must be a safe version identifier")
        String targetVersion,
        @NotBlank @Size(max = 128) String idempotencyKey
) {
}
