package io.incidentcopilot.simulator.error;

public class ScenarioNotFoundException extends RuntimeException {

    public ScenarioNotFoundException(String scenarioKey) {
        super("Unknown scenario: " + scenarioKey);
    }
}
