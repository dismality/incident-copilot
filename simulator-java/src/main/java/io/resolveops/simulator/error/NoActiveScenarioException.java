package io.resolveops.simulator.error;

public class NoActiveScenarioException extends RuntimeException {

    public NoActiveScenarioException() {
        super("No scenario is active. Start one with POST /api/scenarios/{scenarioKey}/start.");
    }
}
