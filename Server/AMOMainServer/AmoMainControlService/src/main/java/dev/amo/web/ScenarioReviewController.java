package dev.amo.web;

import dev.amo.scenarios.application.ReviewHistory.Counts;
import dev.amo.scenarios.application.ReviewResetService;
import dev.amo.scenarios.application.ScenarioReviewService;
import dev.amo.scenarios.application.ScenarioReviewService.View;
import dev.amo.scenarios.application.ScenarioStore.Summary;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Admin-only review endpoints, available in the isolated demo profile. */
@RestController
@Profile("demo")
@RequestMapping("/api/admin/demo/scenarios")
class ScenarioReviewController {
  private final ScenarioReviewService review;
  private final ReviewResetService reset;

  ScenarioReviewController(ScenarioReviewService review, ReviewResetService reset) {
    this.review = review;
    this.reset = reset;
  }

  @GetMapping
  Catalog catalog(@AuthenticationPrincipal Jwt token) {
    return new Catalog(
        Arrays.stream(Scenario.values())
            .map(plan -> new Plan(plan, plan.steps(), List.of()))
            .toList(),
        review.latest(owner(token)),
        reset.counts());
  }

  @PostMapping("/runs")
  View start(@AuthenticationPrincipal Jwt token, @Valid @RequestBody Start body) {
    return review.start(owner(token), body.id(), body.plan());
  }

  @GetMapping("/runs/{id}")
  View read(@AuthenticationPrincipal Jwt token, @PathVariable UUID id) {
    return review.read(owner(token), id);
  }

  @PostMapping("/runs/{id}/steps/{step}")
  View advance(
      @AuthenticationPrincipal Jwt token,
      @PathVariable UUID id,
      @PathVariable Step step,
      @RequestBody Input input) {
    return review.advance(owner(token), id, step, input.manual(), Instant.now());
  }

  @GetMapping("/history")
  History history(@AuthenticationPrincipal Jwt token) {
    return new History(review.history(owner(token)));
  }

  @PostMapping("/runs/{id}/reset")
  Counts resetCurrent(@AuthenticationPrincipal Jwt token, @PathVariable UUID id) {
    return reset.close(owner(token), id);
  }

  @PostMapping("/history/reset")
  Counts resetHistory(@RequestBody Counts expected) {
    return reset.clear(expected);
  }

  private static long owner(Jwt token) {
    return Long.parseLong(token.getSubject());
  }

  record Catalog(List<Plan> plans, View latest, Counts history) {}

  record History(List<Summary> runs) {}

  record Plan(Scenario id, List<Step> steps, List<Step> manualSteps) {}

  record Start(@NotNull UUID id, @NotNull Scenario plan) {}

  record Input(boolean manual) {}
}
