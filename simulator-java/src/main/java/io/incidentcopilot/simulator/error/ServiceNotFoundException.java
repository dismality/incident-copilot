package io.incidentcopilot.simulator.error;

public class ServiceNotFoundException extends RuntimeException {

    public ServiceNotFoundException(String service) {
        super("Service is not part of the active scenario: " + service);
    }
}
