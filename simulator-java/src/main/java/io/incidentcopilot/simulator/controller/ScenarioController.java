package io.incidentcopilot.simulator.controller;

import io.incidentcopilot.simulator.model.ScenarioActivation;
import io.incidentcopilot.simulator.model.ScenarioSummary;
import io.incidentcopilot.simulator.service.SimulatorService;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@Validated
@RestController
@RequestMapping("/api/scenarios")
public class ScenarioController {

    private final SimulatorService simulatorService;

    public ScenarioController(SimulatorService simulatorService) {
        this.simulatorService = simulatorService;
    }

    @GetMapping
    public List<ScenarioSummary> listScenarios() {
        return simulatorService.listScenarios();
    }

    @PostMapping("/{scenarioKey}/start")
    @ResponseStatus(HttpStatus.OK)
    public ScenarioActivation startScenario(@PathVariable String scenarioKey) {
        return simulatorService.startScenario(scenarioKey);
    }
}
