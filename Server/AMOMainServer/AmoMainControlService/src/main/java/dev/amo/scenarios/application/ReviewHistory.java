package dev.amo.scenarios.application;

import java.util.Optional;
import java.util.UUID;

/** Persistence boundary for closing the live review and removing its isolated history. */
public interface ReviewHistory {
  /** Returns review-only counts and the current run used to confirm a history reset. */
  Counts counts();

  /** Closes the current run owned by this administrator if its ID still matches. */
  boolean close(long owner, UUID expected);

  /** Deletes review-only records if the counts still match under the review lock. */
  Optional<Counts> clear(Counts expected);

  /** Counts of isolated runs and observations, and the active run ID when present. */
  record Counts(int runs, int observations, UUID current) {}
}
