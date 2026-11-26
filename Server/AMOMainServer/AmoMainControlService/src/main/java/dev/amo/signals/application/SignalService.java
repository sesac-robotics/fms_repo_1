package dev.amo.signals.application;

import dev.amo.signals.domain.SignalCommand;
import dev.amo.signals.domain.SignalState;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Records signal state from the bridge and queues staff commands for it. The signal keeps its own
 * timing; Main Control only observes and requests holds or plan changes.
 */
@Service
public class SignalService {
  private final SignalStore store;

  SignalService(SignalStore store) {
    this.store = store;
  }

  /**
   * Store a state report as the signal's latest.
   *
   * @param receivedAt UTC time Main Control accepted the report
   * @return false when the report breaks a cross-field rule and was not stored
   */
  public boolean record(SignalState state, Instant receivedAt) {
    if (!state.valid()) {
      return false;
    }
    store.saveState(state, receivedAt);
    return true;
  }

  /** Latest state of every signal that has reported, ordered by signal ID. */
  public List<SignalState.Received> latest() {
    return store.latest();
  }

  /**
   * Queue a staff command for the bridge.
   *
   * <p>A signal must have reported at least once, so a mistyped ID cannot collect commands that no
   * device will ever claim.
   *
   * @param memberId staff member recorded as the requester
   * @param now UTC request time
   */
  @Transactional
  public Issued issue(String signalId, String text, long memberId, Instant now) {
    var command = SignalCommand.parse(text);
    if (command.isEmpty()) {
      return Issued.invalidCommand();
    }
    if (!store.hasReported(signalId)) {
      return Issued.unknownSignal();
    }
    return Issued.queued(store.queue(signalId, command.get(), memberId, now));
  }

  /** Hand the bridge every command it has not received yet, oldest first. */
  @Transactional
  public List<SignalCommand.Pending> claim(String signalId, Instant now) {
    return store.claim(signalId, now);
  }

  /** Outcome of {@link #issue}: a queued command ID, or why nothing was queued. */
  public record Issued(Outcome outcome, long id) {
    /** Why a command was or was not queued. */
    public enum Outcome {
      QUEUED,
      INVALID_COMMAND,
      UNKNOWN_SIGNAL
    }

    static Issued queued(long id) {
      return new Issued(Outcome.QUEUED, id);
    }

    static Issued invalidCommand() {
      return new Issued(Outcome.INVALID_COMMAND, 0);
    }

    static Issued unknownSignal() {
      return new Issued(Outcome.UNKNOWN_SIGNAL, 0);
    }
  }
}
