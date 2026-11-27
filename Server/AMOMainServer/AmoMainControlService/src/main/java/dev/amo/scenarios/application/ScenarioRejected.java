package dev.amo.scenarios.application;

/** Expected rejection for an invalid or incomplete local review action. */
public final class ScenarioRejected extends RuntimeException {
  /** Creates a rejection from a stable API error code. */
  public ScenarioRejected(String code) {
    super(code);
  }
}
