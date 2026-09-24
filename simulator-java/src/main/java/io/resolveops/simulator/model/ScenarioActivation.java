package io.resolveops.simulator.model;

public record ScenarioActivation(
        String scenarioKey,
        String title,
        String description,
        Alert alert
) {
}
