package dev.amo.fares.application;

import dev.amo.fares.domain.Fare.Estimate;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Report;
import dev.amo.fares.domain.RouteChange.Scope;
import java.time.Instant;
import java.util.Optional;

/** Transactional persistence of route and command evidence under the request row lock. */
public interface RouteChangeStore {
  /** Returns the trusted demo target and estimated trip totals for a known demo map place. */
  Optional<Target> target(long requestId, String destination);

  /** Returns the latest proposal and its command scope for the trip. */
  Optional<Proposal> latest(long tripId);

  /** Returns the actually applied proposal, independently of any newer proposal. */
  Optional<Proposal> applied(long tripId);

  /** Returns successfully paid differences for actually applied route revisions. */
  long appliedPayments(long tripId);

  /** Persists the new proposal and quote from validated server-side terms. */
  Proposal propose(long requestId, Work work, Target target, long deltaMinor, Instant now);

  /** Records the first passenger decision on the current terms. */
  void accept(Proposal proposal, String key, Instant now);

  /** Allocates a local replay command without connecting to vehicle hardware. */
  Scope issue(long requestId, Work work, Proposal proposal, Instant now);

  /** Records a matched synthetic command report and conditionally applies the route. */
  void report(long requestId, Scope scope, Report report, Instant now);

  /** The active trip identity. */
  record Work(long vehicleId, long dispatchId, long tripId) {}

  /** Supported destination and schematic quote inputs for the local demo. */
  record Target(long id, long mapVersionId, String placeKey, Estimate estimate) {}
}
