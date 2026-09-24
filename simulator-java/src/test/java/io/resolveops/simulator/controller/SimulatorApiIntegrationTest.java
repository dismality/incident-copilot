package io.resolveops.simulator.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class SimulatorApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void listsScenarioCatalogueAndStartsScenarioUsingContractShape() throws Exception {
        mockMvc.perform(get("/api/scenarios"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(5)))
                .andExpect(content().string(containsString("bad-deployment")));

        mockMvc.perform(post("/api/scenarios/bad-deployment/start"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.scenarioKey").value("bad-deployment"))
                .andExpect(jsonPath("$.alert.alertType").value("high_error_rate"))
                .andExpect(jsonPath("$.alert.service").value("checkout-api"))
                .andExpect(jsonPath("$.alert.startedAt").value("2026-09-24T10:32:00Z"));
    }

    @Test
    void exposesInvestigationEvidenceForActiveService() throws Exception {
        start("bad-deployment");

        mockMvc.perform(get("/api/services/checkout-api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.healthy").value(false))
                .andExpect(jsonPath("$.version").value("2.8.1"));

        mockMvc.perform(get("/api/services/checkout-api/logs").param("minutes", "30"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)))
                .andExpect(content().string(containsString("PaymentAdapterTimeout")));

        mockMvc.perform(get("/api/services/checkout-api/deployments"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)));

        mockMvc.perform(get("/api/services/checkout-api/dependencies"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].status").value("healthy"));
    }

    @Test
    void actionResponseIsIdempotentAndIncludesResultingHealth() throws Exception {
        start("bad-deployment");
        String body = """
                {"targetVersion":"2.8.0","idempotencyKey":"incident-42-action-1"}
                """;

        String firstResponse = mockMvc.perform(post("/api/services/checkout-api/actions/rollback")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.idempotencyKey").value("incident-42-action-1"))
                .andExpect(jsonPath("$.health.healthy").value(true))
                .andExpect(jsonPath("$.health.version").value("2.8.0"))
                .andReturn()
                .getResponse()
                .getContentAsString();

        mockMvc.perform(post("/api/services/checkout-api/actions/rollback")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(content().json(firstResponse, true));
    }

    @Test
    void validatesActionBodiesAndQueryParameters() throws Exception {
        start("traffic-surge");

        mockMvc.perform(post("/api/services/search-api/actions/scale")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"replicas\":21,\"idempotencyKey\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors.replicas").exists())
                .andExpect(jsonPath("$.fieldErrors.idempotencyKey").exists());

        mockMvc.perform(get("/api/services/search-api/logs").param("minutes", "0"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Request validation failed."));
    }

    @Test
    void returns404ForUnknownScenarioAndService() throws Exception {
        mockMvc.perform(post("/api/scenarios/does-not-exist/start"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Unknown scenario: does-not-exist"));

        start("bad-deployment");
        mockMvc.perform(get("/api/services/search-api/health"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Service is not part of the active scenario: search-api"));
    }

    @Test
    void allowsDashboardCorsPreflight() throws Exception {
        mockMvc.perform(options("/api/scenarios")
                        .header("Origin", "http://localhost:8501")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:8501"));
    }

    private void start(String scenarioKey) throws Exception {
        mockMvc.perform(post("/api/scenarios/{scenarioKey}/start", scenarioKey))
                .andExpect(status().isOk());
    }
}
