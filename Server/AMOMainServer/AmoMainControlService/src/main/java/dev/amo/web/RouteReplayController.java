package dev.amo.web;

import dev.amo.fares.application.RouteReplayService;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Report;
import dev.amo.fares.domain.RouteChange.Scope;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Maps strictly scoped mock route commands and reports for an authenticated demo administrator. */
@RestController
@Profile("demo")
@RequestMapping("/api/admin/demo/rides/{requestId}/route")
class RouteReplayController {
  private final RouteReplayService routes;

  RouteReplayController(RouteReplayService routes) {
    this.routes = routes;
  }

  @PostMapping("/propose")
  Proposal propose(@PathVariable long requestId, @Valid @RequestBody Target body) {
    return routes.propose(requestId, body.destination(), Instant.now());
  }

  @PostMapping("/issue")
  Scope issue(@PathVariable long requestId, @Valid @RequestBody Issue body) {
    return routes.issue(requestId, body.revisionId(), Instant.now());
  }

  @PostMapping("/report")
  Proposal report(@PathVariable long requestId, @Valid @RequestBody Observation body) {
    return routes.report(requestId, body.scope(), body.report(), Instant.now());
  }

  record Target(@NotBlank @Pattern(regexp = "S[1-4]") String destination) {}

  record Issue(@Positive long revisionId) {}

  record Observation(
      @Positive long vehicleId,
      @Positive long dispatchId,
      @Positive long revisionId,
      @Positive long commandId,
      @NotBlank @Size(max = 128) String epoch,
      @NotNull Report report) {
    Scope scope() {
      return new Scope(vehicleId, dispatchId, revisionId, commandId, epoch);
    }
  }
}
