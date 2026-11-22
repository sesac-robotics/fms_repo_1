package dev.amo.maincontrol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import dev.amo.maincontrol.MainControlFailure.Reason;
import dev.amo.maincontrol.RideStore.StoredRide;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class RideServiceTest {
  private static final Instant CALLED = Instant.parse("2026-11-22T00:00:00Z");
  private static final Instant RECEIVED = CALLED.plusSeconds(1);
  private static final Ride RIDE =
      new Ride(10, "S1", "S2", "RECEIVED", null, CALLED, RECEIVED, null, null);

  private final RideStore store = mock(RideStore.class);
  private final RideService service = new RideService(store);

  @Test
  void rejectsIdenticalStopsBeforeUsingStorage() {
    assertEquals(
        Reason.IDENTICAL_STOPS,
        assertThrows(MainControlFailure.class, () -> service.accept(5, "S1", "S1", "key", CALLED))
            .reason());
    verifyNoInteractions(store);
  }

  @Test
  void emitsReceiptOnceAndReturnsOriginalTimesOnRetry() {
    stops();
    when(store.insert(5, 1, 2, "key", CALLED)).thenReturn(true, false);
    when(store.byKey(5, "key")).thenReturn(new StoredRide(RIDE, "ONE_WAY", 1, 2L, null));

    assertSame(RIDE, service.accept(5, "S1", "S2", "key", CALLED));
    assertSame(RIDE, service.accept(5, "S1", "S2", "key", CALLED));
    verify(store).accepted(10);
  }

  @Test
  void rejectsAnExistingKeyForADifferentServiceEvenWithTheSameStops() {
    stops();
    when(store.byKey(5, "key")).thenReturn(new StoredRide(RIDE, "RENTAL", 1, 2L, 3600));

    assertEquals(
        Reason.IDEMPOTENCY_KEY_CONFLICT,
        assertThrows(MainControlFailure.class, () -> service.accept(5, "S1", "S2", "key", CALLED))
            .reason());
    verify(store, never()).accepted(10);
  }

  private void stops() {
    when(store.stop("S1")).thenReturn(Optional.of(1L));
    when(store.stop("S2")).thenReturn(Optional.of(2L));
  }
}
