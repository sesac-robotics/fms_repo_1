package dev.amo.web;

import dev.amo.replay.application.DepotReplayService;
import dev.amo.replay.domain.DepotReplay.Observation;
import dev.amo.replay.domain.DepotReplay.Result;
import dev.amo.replay.domain.DepotReplay.Step;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Accepts mock vehicle and facility evidence from an authenticated demo administrator. */
@RestController
@Profile("demo")
class DepotReplayController {
  private final DepotReplayService replay;

  DepotReplayController(DepotReplayService replay) {
    this.replay = replay;
  }

  @PostMapping("/api/admin/demo/depot/observe")
  Result observe(@Valid @RequestBody Body body) {
    return replay.observe(
        body.requestId(), new Observation(body.step(), body.key(), body.batteryPercent()));
  }

  record Body(
      @Positive Long requestId,
      @NotNull Step step,
      @NotBlank @Size(max = 128) String key,
      Double batteryPercent) {}
}
