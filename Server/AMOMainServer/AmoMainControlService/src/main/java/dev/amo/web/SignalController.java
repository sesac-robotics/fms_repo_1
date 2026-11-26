package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.signals.application.SignalService;
import dev.amo.signals.domain.SignalCommand;
import dev.amo.signals.domain.SignalState;
import dev.amo.signals.domain.SignalState.Mode;
import dev.amo.signals.domain.SignalState.Phase;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Signal state from the ROS 2 bridge, the bridge's command queue, and staff commands. */
@RestController
class SignalController {
  static final String SIGNAL_ID = "[A-Z0-9-]{1,32}";
  private final SignalService signals;

  SignalController(SignalService signals) {
    this.signals = signals;
  }

  @PostMapping(path = "/internal/signals/state", consumes = "application/json")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  void record(@Valid @RequestBody State input) {
    if (!signals.record(input.state(), Instant.now())) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_SIGNAL_STATE");
    }
  }

  @GetMapping("/internal/signals/{signalId}/commands")
  List<SignalCommand.Pending> claim(@PathVariable String signalId) {
    return signals.claim(checked(signalId), Instant.now());
  }

  @PostMapping(path = "/api/signals/{signalId}/commands", consumes = "application/json")
  @ResponseStatus(HttpStatus.ACCEPTED)
  Map<String, Long> issue(
      @AuthenticationPrincipal Jwt actor,
      @PathVariable String signalId,
      @Valid @RequestBody Command body) {
    long member = Long.parseLong(actor.getSubject());
    var issued = signals.issue(checked(signalId), body.command(), member, Instant.now());
    return switch (issued.outcome()) {
      case QUEUED -> Map.of("id", issued.id());
      case INVALID_COMMAND -> throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_SIGNAL_COMMAND");
      case UNKNOWN_SIGNAL -> throw new ApiError(HttpStatus.NOT_FOUND, "SIGNAL_NOT_FOUND");
    };
  }

  private static String checked(String signalId) {
    if (!signalId.matches(SIGNAL_ID)) {
      throw new ApiError(HttpStatus.NOT_FOUND, "SIGNAL_NOT_FOUND");
    }
    return signalId;
  }

  record Command(@NotNull @Size(max = 40) String command) {}

  /** The firmware's state JSON, forwarded unchanged by the bridge. */
  record State(
      @NotNull @Pattern(regexp = SIGNAL_ID) String signalId,
      @Min(0) long seq,
      @NotNull Phase phase,
      @NotNull Mode mode,
      Phase holdTarget,
      @Min(0) @Max(600_000) int remainingMs,
      @Min(0) long uptimeMs,
      @NotNull @Size(min = 4, max = 4) List<@NotNull Integer> planMs,
      boolean planPending,
      @NotNull @Size(max = 40) String lastCommand,
      @NotNull @Pattern(regexp = "[A-Z_]{1,20}") String commandResult) {
    SignalState state() {
      return new SignalState(
          signalId,
          seq,
          phase,
          mode,
          holdTarget,
          remainingMs,
          uptimeMs,
          new SignalCommand.Timing(planMs.get(0), planMs.get(1), planMs.get(2), planMs.get(3)),
          planPending,
          lastCommand,
          commandResult);
    }
  }
}
