package io.resolveops.simulator.service;

import io.resolveops.simulator.error.NoActiveScenarioException;
import io.resolveops.simulator.error.ScenarioNotFoundException;
import io.resolveops.simulator.error.ServiceNotFoundException;
import io.resolveops.simulator.model.ActionExecution;
import io.resolveops.simulator.model.DependencyStatus;
import io.resolveops.simulator.model.ServiceHealth;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SimulatorServiceTest {

    private SimulatorService simulator;

    @BeforeEach
    void setUp() {
        simulator = new SimulatorService();
    }

    @Test
    void exposesFiveScenarioDefinitions() {
        assertThat(simulator.listScenarios())
                .extracting(scenario -> scenario.scenarioKey())
                .containsExactlyInAnyOrder(
                        "bad-deployment",
                        "traffic-surge",
                        "disk-pressure",
                        "provider-outage",
                        "ambiguous-login"
                );
    }

    @Test
    void rejectsReadsUntilAScenarioIsStarted() {
        assertThatThrownBy(() -> simulator.getHealth("checkout-api"))
                .isInstanceOf(NoActiveScenarioException.class);
    }

    @Test
    void rejectsUnknownScenariosAndServices() {
        assertThatThrownBy(() -> simulator.startScenario("not-real"))
                .isInstanceOf(ScenarioNotFoundException.class);

        simulator.startScenario("bad-deployment");
        assertThatThrownBy(() -> simulator.getHealth("search-api"))
                .isInstanceOf(ServiceNotFoundException.class);
    }

    @Test
    void rollbackRecoversBadDeployment() {
        simulator.startScenario("bad-deployment");

        ActionExecution execution = simulator.rollback(
                "checkout-api", "2.8.0", "incident-1-action-1"
        );

        assertThat(execution.success()).isTrue();
        assertThat(execution.action()).isEqualTo("rollback_deployment");
        assertThat(execution.health().healthy()).isTrue();
        assertThat(execution.health().version()).isEqualTo("2.8.0");
        assertThat(execution.health().errorRate()).isLessThan(0.02);
        assertThat(simulator.getDeployments("checkout-api"))
                .filteredOn(deployment -> deployment.version().equals("2.8.0"))
                .singleElement()
                .extracting(deployment -> deployment.status())
                .isEqualTo("active");
    }

    @Test
    void duplicateIdempotencyKeyReturnsTheOriginalExecutionWithoutAnotherMutation() {
        simulator.startScenario("traffic-surge");

        ActionExecution first = simulator.scale("search-api", 10, "same-key");
        ActionExecution duplicateWithDifferentArguments = simulator.scale("search-api", 15, "same-key");

        assertThat(duplicateWithDifferentArguments).isSameAs(first);
        assertThat(simulator.getHealth("search-api").replicas()).isEqualTo(10);
    }

    @Test
    void scaleRecoversTrafficSurgeAtTenReplicas() {
        simulator.startScenario("traffic-surge");

        ActionExecution execution = simulator.scale("search-api", 10, "scale-10");

        assertThat(execution.success()).isTrue();
        assertThat(execution.health().healthy()).isTrue();
        assertThat(execution.health().replicas()).isEqualTo(10);
        assertThat(execution.health().latencyMs()).isLessThan(800);
        assertThat(execution.health().cpuPercent()).isLessThan(70);
    }

    @Test
    void cleanupRecoversDiskPressureWithoutTouchingProtectedData() {
        simulator.startScenario("disk-pressure");

        ActionExecution execution = simulator.cleanup(
                "reporting-worker", 7, "cleanup-expired"
        );

        assertThat(execution.health().healthy()).isTrue();
        assertThat(execution.health().diskFreePercent()).isGreaterThan(25.0);
        assertThat(execution.health().details())
                .containsEntry("removedExportGb", 145)
                .containsEntry("protectedApplicationDataGb", 32);
    }

    @Test
    void restartDoesNotHideExternalProviderOutage() {
        simulator.startScenario("provider-outage");

        ActionExecution execution = simulator.restart("notification-service", "restart-1");
        DependencyStatus provider = simulator.getDependencies("notification-service").stream()
                .filter(dependency -> dependency.name().equals("email-provider"))
                .findFirst()
                .orElseThrow();

        assertThat(execution.success()).isTrue();
        assertThat(execution.health().healthy()).isFalse();
        assertThat(provider.status()).isEqualTo("outage");
        assertThat(execution.message()).contains("remains unavailable");
    }

    @Test
    void ambiguousScenarioContainsUntrustedLogEvidenceAndDoesNotSelfResolve() {
        simulator.startScenario("ambiguous-login");

        assertThat(simulator.getLogs("auth-service", 30))
                .anySatisfy(entry -> assertThat(entry.message()).contains("UNTRUSTED USER TEXT"));

        ServiceHealth health = simulator.getHealth("auth-service");
        assertThat(health.healthy()).isFalse();
        assertThat(health.details()).containsEntry("evidenceCompleteness", "low");
    }

    @Test
    void startingAScenarioAgainRestoresItsOriginalStateAndIdempotencyScope() {
        simulator.startScenario("bad-deployment");
        simulator.rollback("checkout-api", "2.8.0", "rollback-key");
        assertThat(simulator.getHealth("checkout-api").healthy()).isTrue();

        simulator.startScenario("bad-deployment");

        assertThat(simulator.getHealth("checkout-api").healthy()).isFalse();
        assertThat(simulator.getHealth("checkout-api").version()).isEqualTo("2.8.1");
        ActionExecution nextRun = simulator.rollback("checkout-api", "2.8.0", "rollback-key");
        assertThat(nextRun.health().healthy()).isTrue();
    }
}
