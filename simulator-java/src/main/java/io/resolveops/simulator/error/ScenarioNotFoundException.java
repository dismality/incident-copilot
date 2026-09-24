package io.resolveops.simulator.error;

public class ScenarioNotFoundException extends RuntimeException {

    public ScenarioNotFoundException(String scenarioKey) {
        super("Unknown scenario: " + scenarioKey);
    }
}
