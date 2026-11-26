package dev.amo.signals.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.amo.signals.application.SignalService.Issued.Outcome;
import dev.amo.signals.domain.SignalCommand;
import dev.amo.signals.domain.SignalCommand.Pending;
import dev.amo.signals.domain.SignalCommand.Timing;
import dev.amo.signals.domain.SignalState;
import dev.amo.signals.domain.SignalState.Mode;
import dev.amo.signals.domain.SignalState.Phase;
import dev.amo.signals.domain.SignalState.Received;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SignalServiceTest {
  private static final Instant NOW = Instant.parse("2026-11-26T06:00:00Z");
  private final MemoryStore store = new MemoryStore();
  private final SignalService service = new SignalService(store);

  @Test
  void storesOnlyConsistentReports() {
    assertTrue(service.record(state(Mode.AUTO, null), NOW));
    assertFalse(service.record(state(Mode.HOLD, null), NOW));
    assertEquals(1, service.latest().size());
  }

  @Test
  void queuesSafeCommandsForAReportedSignalAndHandsThemOutOnce() {
    service.record(state(Mode.AUTO, null), NOW);
    var first = service.issue("SIG-01", "HOLD NORTH_GREEN", 7, NOW);
    var second = service.issue("SIG-01", "PLAN 15000 8000 3000 2000", 7, NOW);
    assertEquals(Outcome.QUEUED, first.outcome());
    assertEquals(Outcome.QUEUED, second.outcome());
    var claimed = service.claim("SIG-01", NOW);
    assertEquals(List.of("HOLD NORTH_GREEN", "PLAN 15000 8000 3000 2000"), commands(claimed));
    assertTrue(service.claim("SIG-01", NOW).isEmpty());
  }

  @Test
  void rejectsUnsafeCommandsAndSignalsThatNeverReported() {
    service.record(state(Mode.AUTO, null), NOW);
    assertEquals(
        Outcome.INVALID_COMMAND,
        service.issue("SIG-01", "PLAN 1000 8000 3000 2000", 7, NOW).outcome());
    assertEquals(Outcome.UNKNOWN_SIGNAL, service.issue("SIG-99", "AUTO", 7, NOW).outcome());
    assertTrue(service.claim("SIG-99", NOW).isEmpty());
  }

  private static List<String> commands(List<Pending> pending) {
    return pending.stream().map(Pending::command).toList();
  }

  private static SignalState state(Mode mode, Phase hold) {
    return new SignalState(
        "SIG-01",
        1,
        Phase.ALL_RED,
        mode,
        hold,
        0,
        1_000,
        new Timing(10_000, 10_000, 3_000, 2_000),
        false,
        "",
        "NONE");
  }

  /** In-memory store with the same claim-once behaviour as the JDBC adapter. */
  private static final class MemoryStore implements SignalStore {
    private final Map<String, Received> latest = new LinkedHashMap<>();
    private final List<Pending> queued = new ArrayList<>();
    private long nextId = 1;

    @Override
    public void saveState(SignalState state, Instant receivedAt) {
      latest.put(state.signalId(), new Received(state, receivedAt));
    }

    @Override
    public List<Received> latest() {
      return List.copyOf(latest.values());
    }

    @Override
    public boolean hasReported(String signalId) {
      return latest.containsKey(signalId);
    }

    @Override
    public long queue(String signalId, SignalCommand command, long requestedBy, Instant at) {
      queued.add(new Pending(nextId, signalId, command.text()));
      return nextId++;
    }

    @Override
    public List<Pending> claim(String signalId, Instant deliveredAt) {
      var mine = queued.stream().filter(p -> p.signalId().equals(signalId)).toList();
      queued.removeAll(mine);
      return mine;
    }
  }
}
