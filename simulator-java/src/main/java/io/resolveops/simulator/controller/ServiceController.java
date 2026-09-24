package io.resolveops.simulator.controller;

import io.resolveops.simulator.model.ActionExecution;
import io.resolveops.simulator.model.CleanupRequest;
import io.resolveops.simulator.model.DependencyStatus;
import io.resolveops.simulator.model.Deployment;
import io.resolveops.simulator.model.LogEntry;
import io.resolveops.simulator.model.RestartRequest;
import io.resolveops.simulator.model.RollbackRequest;
import io.resolveops.simulator.model.ScaleRequest;
import io.resolveops.simulator.model.ServiceHealth;
import io.resolveops.simulator.service.SimulatorService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@Validated
@RestController
@RequestMapping("/api/services/{service}")
public class ServiceController {

    private static final String SERVICE_PATTERN = "[A-Za-z0-9][A-Za-z0-9._-]*";

    private final SimulatorService simulatorService;

    public ServiceController(SimulatorService simulatorService) {
        this.simulatorService = simulatorService;
    }

    @GetMapping("/health")
    public ServiceHealth getHealth(@PathVariable @Pattern(regexp = SERVICE_PATTERN) String service) {
        return simulatorService.getHealth(service);
    }

    @GetMapping("/logs")
    public List<LogEntry> getLogs(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service,
            @RequestParam(defaultValue = "30") @Min(1) @Max(1_440) int minutes
    ) {
        return simulatorService.getLogs(service, minutes);
    }

    @GetMapping("/deployments")
    public List<Deployment> getDeployments(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service
    ) {
        return simulatorService.getDeployments(service);
    }

    @GetMapping("/dependencies")
    public List<DependencyStatus> getDependencies(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service
    ) {
        return simulatorService.getDependencies(service);
    }

    @PostMapping("/actions/rollback")
    public ActionExecution rollback(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service,
            @Valid @RequestBody RollbackRequest request
    ) {
        return simulatorService.rollback(service, request.targetVersion(), request.idempotencyKey());
    }

    @PostMapping("/actions/scale")
    public ActionExecution scale(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service,
            @Valid @RequestBody ScaleRequest request
    ) {
        return simulatorService.scale(service, request.replicas(), request.idempotencyKey());
    }

    @PostMapping("/actions/restart")
    public ActionExecution restart(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service,
            @Valid @RequestBody RestartRequest request
    ) {
        return simulatorService.restart(service, request.idempotencyKey());
    }

    @PostMapping("/actions/cleanup")
    public ActionExecution cleanup(
            @PathVariable @Pattern(regexp = SERVICE_PATTERN) String service,
            @Valid @RequestBody CleanupRequest request
    ) {
        return simulatorService.cleanup(service, request.olderThanDays(), request.idempotencyKey());
    }
}
