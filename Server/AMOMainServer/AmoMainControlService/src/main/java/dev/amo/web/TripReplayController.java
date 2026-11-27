package dev.amo.web;

import dev.amo.replay.application.TripReplayService;
import dev.amo.replay.application.TripReplayService.Result;
import dev.amo.replay.domain.TripReplay.Step;
import dev.amo.replay.domain.TripReplay.Totals;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Accepts authenticated staff replay steps on the local demo profile only. */
@RestController
@Profile("demo")
class TripReplayController {
  private final TripReplayService replay;

  TripReplayController(TripReplayService replay) {
    this.replay = replay;
  }

  @PostMapping("/api/admin/demo/rides/{requestId}/observe")
  Result observe(@PathVariable long requestId, @Valid @RequestBody Observation body) {
    return replay.observe(requestId, body.step(), body.totals());
  }

  record Observation(
      @NotNull Step step,
      @PositiveOrZero Double distanceMeters,
      @PositiveOrZero Integer elapsedSeconds) {
    Totals totals() {
      if (distanceMeters == null && elapsedSeconds == null) {
        return null;
      }
      if (distanceMeters == null || elapsedSeconds == null || !Double.isFinite(distanceMeters)) {
        throw new TripReplayService.ReplayFailure("DEMO_TOTALS_INVALID");
      }
      return new Totals(distanceMeters, elapsedSeconds);
    }
  }
}
