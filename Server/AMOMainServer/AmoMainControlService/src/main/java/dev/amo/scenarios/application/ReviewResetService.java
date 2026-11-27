package dev.amo.scenarios.application;

import dev.amo.scenarios.application.ReviewHistory.Counts;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Destructive actions are confined to the review transaction and its isolated records. */
@Service
@Profile("demo")
public class ReviewResetService {
  private final ScenarioStore store;
  private final ReviewHistory history;

  ReviewResetService(ScenarioStore store, ReviewHistory history) {
    this.store = store;
    this.history = history;
  }

  /** Returns isolated counts to display before confirming the reset. */
  @Transactional(readOnly = true)
  public Counts counts() {
    return history.counts();
  }

  /** Stops playback without erasing its evidence. Rejects a stale or unowned current ID. */
  @Transactional
  public Counts close(long owner, UUID expected) {
    store.enterReview();
    if (!history.close(owner, expected)) {
      throw new ScenarioRejected("SCENARIO_RUN_SUPERSEDED");
    }
    return history.counts();
  }

  /** Removes isolated history only if it still matches the explicit confirmation. */
  @Transactional
  public Counts clear(Counts expected) {
    store.enterReview();
    history.clear(expected).orElseThrow(() -> new ScenarioRejected("SCENARIO_RESET_CHANGED"));
    return history.counts();
  }
}
