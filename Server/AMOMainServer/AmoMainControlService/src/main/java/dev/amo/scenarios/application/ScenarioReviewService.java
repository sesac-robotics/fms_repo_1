package dev.amo.scenarios.application;

import dev.amo.scenarios.application.ScenarioStore.Played;
import dev.amo.scenarios.application.ScenarioStore.Run;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Coordinates a review run and commits one business step with its observed result. */
@Service
@Profile("demo")
public class ScenarioReviewService {
  private final ScenarioStore store;
  private final ScenarioSteps steps;

  ScenarioReviewService(ScenarioStore store, ScenarioSteps steps) {
    this.store = store;
    this.steps = steps;
  }

  /** Creates an isolated run once per stable ID. A repeated start returns its current evidence. */
  @Transactional
  public View start(long owner, UUID id, Scenario plan) {
    Run run =
        store
            .start(owner, id, plan)
            .orElseThrow(() -> new ScenarioRejected("SCENARIO_RUN_UNAVAILABLE"));
    if (run.plan() != plan) {
      throw new ScenarioRejected("SCENARIO_START_CONFLICT");
    }
    return view(run, store.steps(id));
  }

  /** Reads the authenticated administrator's run and its committed evidence. */
  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public View read(long owner, UUID id) {
    return view(owned(owner, id, false), store.steps(id));
  }

  /** Reads the last started run, allowing the same admin to resume after reconnecting. */
  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public View latest(long owner) {
    return store.latest(owner).map(run -> view(run, store.steps(run.id()))).orElse(null);
  }

  /**
   * Runs only the next stage, or returns stored evidence for a repeated click. Manual actions check
   * externally recorded passenger input. The supplied time is a UTC instant.
   */
  @Transactional
  public View advance(long owner, UUID id, Step step, boolean manual, Instant now) {
    Run run = owned(owner, id, true);
    List<Played> previous = store.steps(id);
    if (previous.stream().anyMatch(result -> result.step() == step)) {
      return view(run, previous);
    }
    var ordered = run.plan().steps();
    if (previous.size() >= ordered.size() || ordered.get(previous.size()) != step) {
      throw new ScenarioRejected("SCENARIO_STEP_OUT_OF_ORDER");
    }
    if (manual && !step.acceptsManualInput()) {
      throw new ScenarioRejected("SCENARIO_MANUAL_INPUT_UNSUPPORTED");
    }
    var evidence = steps.execute(run, step, manual, now.truncatedTo(ChronoUnit.MICROS));
    store.record(id, previous.size(), step, evidence);
    var results = new ArrayList<>(previous);
    results.add(new Played(step, evidence));
    return view(owned(owner, id, false), results);
  }

  private Run owned(long owner, UUID id, boolean lock) {
    return store
        .find(owner, id, lock)
        .orElseThrow(() -> new ScenarioRejected("SCENARIO_RUN_NOT_FOUND"));
  }

  private static View view(Run run, List<Played> results) {
    var ordered = run.plan().steps();
    Step next = results.size() == ordered.size() ? null : ordered.get(results.size());
    return new View(
        run.id(), run.plan(), run.vehicleNumber(), run.requestId(), next, List.copyOf(results));
  }

  /** Ordered read model for the review window, with identifiers from persisted business records. */
  public record View(
      UUID id,
      Scenario plan,
      String vehicleNumber,
      Long requestId,
      Step nextStep,
      List<Played> completed) {}
}
