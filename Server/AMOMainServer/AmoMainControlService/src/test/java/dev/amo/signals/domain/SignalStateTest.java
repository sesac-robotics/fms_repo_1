package dev.amo.signals.domain;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.amo.signals.domain.SignalCommand.Timing;
import dev.amo.signals.domain.SignalState.Mode;
import dev.amo.signals.domain.SignalState.Phase;
import org.junit.jupiter.api.Test;

class SignalStateTest {
  private static final Timing DEFAULT = new Timing(10_000, 10_000, 3_000, 2_000);

  @Test
  void acceptsAutoWithoutHoldTargetAndHoldWithAGreenOrAllRedTarget() {
    assertTrue(state(Mode.AUTO, null, DEFAULT).valid());
    assertTrue(state(Mode.HOLD, Phase.NORTH_GREEN, DEFAULT).valid());
    assertTrue(state(Mode.HOLD, Phase.EAST_GREEN, DEFAULT).valid());
    assertTrue(state(Mode.HOLD, Phase.ALL_RED, DEFAULT).valid());
  }

  @Test
  void rejectsInconsistentHoldTargets() {
    assertFalse(state(Mode.AUTO, Phase.NORTH_GREEN, DEFAULT).valid());
    assertFalse(state(Mode.HOLD, null, DEFAULT).valid());
    assertFalse(state(Mode.HOLD, Phase.NORTH_YELLOW, DEFAULT).valid());
  }

  @Test
  void rejectsAReportedPlanOutsideTheSafeRanges() {
    assertFalse(state(Mode.AUTO, null, new Timing(1_000, 10_000, 3_000, 2_000)).valid());
  }

  private static SignalState state(Mode mode, Phase hold, Timing plan) {
    return new SignalState(
        "SIG-01", 1, Phase.ALL_RED, mode, hold, 0, 1_000, plan, false, "", "NONE");
  }
}
