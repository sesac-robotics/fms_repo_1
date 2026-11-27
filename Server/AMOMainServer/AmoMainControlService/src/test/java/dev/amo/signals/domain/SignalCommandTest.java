package dev.amo.signals.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class SignalCommandTest {
  @Test
  void acceptsTheFirmwareCommandWords() {
    for (String text :
        new String[] {"AUTO", "HOLD NORTH_GREEN", "HOLD EAST_GREEN", "HOLD ALL_RED"}) {
      assertEquals(Optional.of(new SignalCommand(text)), SignalCommand.parse(text));
    }
  }

  @Test
  void acceptsAPlanInsideTheSafeRanges() {
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000").isPresent());
    assertTrue(SignalCommand.parse("PLAN 3000 120000 2000 1000").isPresent());
    assertTrue(SignalCommand.parse("PLAN 120000 3000 10000 10000").isPresent());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 4000 17000").isPresent());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 3000 0").isPresent());
    assertTrue(SignalCommand.parse("PLAN 120000 120000 10000 10000 10000 130000").isPresent());
  }

  @Test
  void rejectsUnsafeOrMalformedPlans() {
    assertTrue(SignalCommand.parse("PLAN 2999 8000 3000 2000").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 120001 3000 2000").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 1999 2000").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 999").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 1").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 1999 0").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 3000 4999").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 3000 130001").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000 8000 3000 2000 3000 0 1").isEmpty());
    assertTrue(SignalCommand.parse("PLAN -1 8000 3000 2000").isEmpty());
    assertTrue(SignalCommand.parse("PLAN 15000  8000 3000 2000").isEmpty());
  }

  @Test
  void rejectsUnknownText() {
    assertTrue(SignalCommand.parse(null).isEmpty());
    assertTrue(SignalCommand.parse("").isEmpty());
    assertTrue(SignalCommand.parse("auto").isEmpty());
    assertTrue(SignalCommand.parse("HOLD NORTH_YELLOW").isEmpty());
    assertTrue(SignalCommand.parse("AUTO ").isEmpty());
  }
}
