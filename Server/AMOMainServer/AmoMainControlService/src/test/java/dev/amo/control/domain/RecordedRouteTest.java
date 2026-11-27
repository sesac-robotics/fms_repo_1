package dev.amo.control.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.List;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

class RecordedRouteTest {
  @Test
  void returnsObservedPointsInChronologicalOrder() {
    var route = RecordedRoute.from(42, List.of(sample("boot-1", 2, 0.8), sample("boot-1", 1, 0.4)));

    assertEquals(42, route.requestId());
    assertEquals("v0.2", route.mapVersion());
    assertEquals("schematic_v02", route.frameId());
    assertEquals(
        List.of(List.of(new RecordedRoute.Point(0.4, 1), new RecordedRoute.Point(0.8, 1))),
        route.segments());
    assertFalse(route.truncated());
  }

  @Test
  void splitsWhenASequenceIsMissingOrTheSourceRestarts() {
    var route =
        RecordedRoute.from(
            42,
            List.of(
                sample("boot-2", 10, 1.3),
                sample("boot-2", 9, 1.2),
                sample("boot-1", 8, 1.1),
                sample("boot-1", 7, 1.0),
                sample("boot-1", 2, 0.8),
                sample("boot-1", 1, 0.4)));

    assertEquals(List.of(2, 2, 2), route.segments().stream().map(List::size).toList());
  }

  @Test
  void neverBridgesAnIncompatibleMapOrAnInvalidPosition() {
    var outside = sample("boot-1", 6, 2.8);
    var unsupported =
        new RecordedRoute.Sample("v0.1", "older", "boot-1", 3, Instant.ofEpochSecond(3), 0.9, 1.0);
    var route =
        RecordedRoute.from(
            42,
            List.of(
                sample("boot-1", 7, 1.4),
                outside,
                sample("boot-1", 5, 1.2),
                sample("boot-1", 4, 1.1),
                unsupported,
                sample("boot-1", 2, 0.8),
                sample("boot-1", 1, 0.4)));

    assertEquals(List.of(2, 2), route.segments().stream().map(List::size).toList());
  }

  @Test
  void absentOrStationaryPositionsProduceAnEmptyRoute() {
    for (var samples :
        List.of(
            List.<RecordedRoute.Sample>of(),
            List.of(sample("boot", 1, 0.4)),
            List.of(sample("boot", 2, 0.4), sample("boot", 1, 0.4)))) {
      var route = RecordedRoute.from(42, samples);
      assertNull(route.mapVersion());
      assertNull(route.frameId());
      assertTrue(route.segments().isEmpty());
    }
  }

  @Test
  void signalsWhenOnlyTheMostRecentSamplesFit() {
    var samples =
        IntStream.rangeClosed(1, RecordedRoute.MAX_SAMPLES + 1)
            .mapToObj(sequence -> sample("boot", sequence, sequence / 1_000.0))
            .toList()
            .reversed();
    var route = RecordedRoute.from(42, samples);

    assertTrue(route.truncated());
    assertEquals(RecordedRoute.MAX_SAMPLES, route.segments().getFirst().size());
    assertEquals(0.002, route.segments().getFirst().getFirst().xM());
  }

  private static RecordedRoute.Sample sample(String epoch, long sequence, double xM) {
    return new RecordedRoute.Sample(
        "v0.2", "schematic_v02", epoch, sequence, Instant.ofEpochSecond(sequence), xM, 1.0);
  }
}
