package dev.amo.signals.application;

import dev.amo.signals.domain.SignalCommand;
import dev.amo.signals.domain.SignalState;
import java.time.Instant;
import java.util.List;

/** Persists signal state and the staff command queue. */
public interface SignalStore {
  /** Save the report as the latest for its signal. */
  void saveState(SignalState state, Instant receivedAt);

  /** Latest state of every signal that has reported. */
  List<SignalState.Received> latest();

  /** Whether the signal has reported at least one state. */
  boolean hasReported(String signalId);

  /** Queue a command and return its identifier. */
  long queue(String signalId, SignalCommand command, long requestedBy, Instant requestedAt);

  /** Mark the signal's undelivered commands as delivered and return them in order. */
  List<SignalCommand.Pending> claim(String signalId, Instant deliveredAt);
}
