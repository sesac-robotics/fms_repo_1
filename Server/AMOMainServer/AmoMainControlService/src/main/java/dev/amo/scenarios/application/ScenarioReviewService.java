package dev.amo.scenarios.application;

import dev.amo.scenarios.application.ScenarioStore.Played;
import dev.amo.scenarios.application.ScenarioStore.Run;
import dev.amo.scenarios.application.ScenarioStore.Summary;
import dev.amo.scenarios.domain.ReviewProgress;
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

  /**
   * Starts one review on the shared fixture per stable ID. A repeated start returns its current
   * evidence.
   */
  @Transactional
  public View start(long owner, UUID id, Scenario plan) {
    store.enterReview();
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
    store.enterReview();
    var run = store.find(owner, id, false);
    if (run.isPresent()) {
      return view(run.get(), store.steps(id));
    }
    Run archived =
        store.archived(owner, id).orElseThrow(() -> new ScenarioRejected("SCENARIO_RUN_NOT_FOUND"));
    return view(archived, store.archivedSteps(id));
  }

  /** Lists recent review history only for its authenticated owner. */
  @Transactional(readOnly = true)
  public List<Summary> history(long owner) {
    return store.history(owner);
  }

  /** Reads the last started run, allowing the same admin to resume after reconnecting. */
  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public View latest(long owner) {
    store.enterReview();
    return store.latest(owner).map(run -> view(run, store.steps(run.id()))).orElse(null);
  }

  /**
   * Runs an available stage, or returns stored evidence for a repeated click. Passenger input is
   * simulated inside the review boundary. The supplied time is a UTC instant.
   */
  @Transactional
  public View advance(long owner, UUID id, Step step, boolean manual, Instant now) {
    store.enterReview();
    boolean current = store.lockCurrent(id);
    Run run = owned(owner, id, true);
    List<Played> previous = store.steps(id);
    if (previous.stream().anyMatch(result -> result.step() == step)) {
      return view(run, previous);
    }
    if (!current) {
      throw new ScenarioRejected("SCENARIO_RUN_SUPERSEDED");
    }
    var progress = progress(run, previous);
    if (!progress.available().contains(step)) {
      throw new ScenarioRejected("SCENARIO_STEP_OUT_OF_ORDER");
    }
    if (manual) {
      throw new ScenarioRejected("SCENARIO_MANUAL_INPUT_UNSUPPORTED");
    }
    var evidence =
        steps.execute(
            run.usingRoute(progress.effectiveRoute()), step, now.truncatedTo(ChronoUnit.MICROS));
    store.record(id, previous.size(), step, evidence);
    Run updated = owned(owner, id, false);
    var results = new ArrayList<>(previous);
    results.add(new Played(step, evidence));
    store.project(
        updated.usingRoute(progress(updated, results).effectiveRoute()),
        previous.size(),
        step,
        evidence);
    return view(updated, results);
  }

  private Run owned(long owner, UUID id, boolean lock) {
    return store
        .find(owner, id, lock)
        .orElseThrow(() -> new ScenarioRejected("SCENARIO_RUN_NOT_FOUND"));
  }

  private static View view(Run run, List<Played> results) {
    var progress = progress(run, results);
    return new View(
        run.id(),
        run.plan(),
        run.vehicleNumber(),
        run.requestId(),
        progress.next(),
        List.copyOf(results),
        progress.available());
  }

  private static ReviewProgress progress(Run run, List<Played> results) {
    return ReviewProgress.at(run.plan(), results.stream().map(Played::step).toList());
  }

  /** Ordered read model for the review window, with identifiers from persisted business records. */
  public record View(
      UUID id,
      Scenario plan,
      String vehicleNumber,
      Long requestId,
      Step nextStep,
      List<Played> completed,
      List<Step> availableSteps) {}
}
