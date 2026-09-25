package io.incidentcopilot.simulator.service;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class SimulatorMetrics {

    private static final List<String> SERVICES = List.of(
            "checkout-api",
            "search-api",
            "reporting-worker",
            "notification-service",
            "auth-service"
    );

    public SimulatorMetrics(MeterRegistry registry, SimulatorService simulator) {
        for (String service : SERVICES) {
            register(registry, "incident.service.error.ratio", service,
                    () -> simulator.metricErrorRate(service));
            register(registry, "incident.service.latency.ms", service,
                    () -> simulator.metricLatencyMs(service));
            register(registry, "incident.service.cpu.percent", service,
                    () -> simulator.metricCpuPercent(service));
            register(registry, "incident.service.disk.free.percent", service,
                    () -> simulator.metricDiskFreePercent(service));
            register(registry, "incident.service.queue.depth", service,
                    () -> simulator.metricQueueDepth(service));
        }

        Gauge.builder(
                        "incident.dependency.available",
                        () -> simulator.metricDependencyAvailable(
                                "notification-service", "email-provider"
                        )
                )
                .description("Whether a simulated dependency is available (1=yes, 0=no)")
                .tag("service", "notification-service")
                .tag("dependency", "email-provider")
                .register(registry);
    }

    private static void register(
            MeterRegistry registry,
            String name,
            String service,
            java.util.function.Supplier<Number> supplier
    ) {
        Gauge.builder(name, supplier)
                .description("Deterministic service signal exposed for Prometheus detection")
                .tag("service", service)
                .register(registry);
    }
}
