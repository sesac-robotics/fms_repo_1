package dev.amo.control.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import dev.amo.control.domain.Operations.PinkyBattery;
import dev.amo.signals.application.SignalService;
import dev.amo.signals.domain.SignalCommand.Timing;
import dev.amo.signals.domain.SignalState;
import dev.amo.signals.domain.SignalState.Mode;
import dev.amo.signals.domain.SignalState.Phase;
import dev.amo.vision.application.VisionObservations;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mock.env.MockEnvironment;

class OperationsServiceTest {
  @Test
  @SuppressWarnings("unchecked")
  void snapshotIncludesBothSignalsAndBatteryReadings() {
    var signals = mock(SignalService.class);
    var state =
        new SignalState(
            "SIG-01",
            42,
            Phase.NORTH_GREEN,
            Mode.AUTO,
            null,
            7_300,
            123_456,
            new Timing(10_000, 10_000, 3_000, 2_000),
            false,
            "",
            "NONE");
    var received = new SignalState.Received(state, Instant.parse("2026-11-26T06:00:00Z"));
    when(signals.latest()).thenReturn(List.of(received));
    var battery = new PinkyBattery("PP_00001", 70.0, 8.0, received.receivedAt(), false);
    var service =
        new OperationsService(
            mock(OperationsStore.class),
            mock(RecordedRouteStore.class),
            mock(VisionObservations.class),
            () -> List.of(battery),
            signals,
            new MockEnvironment(),
            mock(ObjectProvider.class));

    var snapshot = service.snapshot();
    assertEquals(List.of(received), snapshot.signals());
    assertEquals(List.of(battery), snapshot.pinkyBatteries());
  }
}
