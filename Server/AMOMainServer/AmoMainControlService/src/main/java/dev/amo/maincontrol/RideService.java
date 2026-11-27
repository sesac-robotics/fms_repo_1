package dev.amo.maincontrol;

import dev.amo.maincontrol.MainControlFailure.Reason;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Receives passenger requests idempotently without booking or moving a vehicle. */
@Service
public class RideService {
  private final RideStore repository;

  RideService(RideStore repository) {
    this.repository = repository;
  }

  /**
   * Records the passenger's optional source time and a separate database receipt time. Replays
   * return the original stored times and do not use the client clock to order dispatch.
   *
   * @param calledAt optional client timestamp in UTC
   * @throws MainControlFailure for identical or unknown stops or reuse of a key for another ride
   */
  @Transactional(isolation = Isolation.READ_COMMITTED)
  public Ride accept(long userId, String pickup, String destination, String key, Instant calledAt) {
    if (pickup.equals(destination)) {
      throw new MainControlFailure(Reason.IDENTICAL_STOPS);
    }
    long pickupId = stopId(pickup);
    long destinationId = stopId(destination);
    boolean created = repository.insert(userId, pickupId, destinationId, key, calledAt);
    var stored = repository.byKey(userId, key);
    if (!stored.matchesOneWay(pickupId, destinationId)) {
      throw new MainControlFailure(Reason.IDEMPOTENCY_KEY_CONFLICT);
    }
    Ride ride = stored.ride();
    if (created) {
      repository.accepted(ride.id());
    }
    return ride;
  }

  /** Returns the passenger's most recent stored requests by server receipt time. */
  @Transactional(readOnly = true)
  public List<Ride> history(long userId) {
    return repository.history(userId);
  }

  private long stopId(String key) {
    return repository.stop(key).orElseThrow(() -> new MainControlFailure(Reason.UNKNOWN_STOP));
  }
}
