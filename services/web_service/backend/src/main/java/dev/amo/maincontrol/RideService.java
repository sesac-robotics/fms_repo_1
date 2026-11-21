package dev.amo.maincontrol;

import dev.amo.ApiError;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Receives passenger requests idempotently without booking or moving a vehicle. */
@Service
public class RideService {
  private final RideRepository repository;

  RideService(RideRepository repository) {
    this.repository = repository;
  }

  @Transactional(isolation = Isolation.READ_COMMITTED)
  public Ride accept(long userId, String pickup, String destination, String key) {
    if (pickup.equals(destination)) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "IDENTICAL_STOPS");
    }
    long pickupId = stopId(pickup);
    long destinationId = stopId(destination);
    boolean created = repository.insert(userId, pickupId, destinationId, key);
    var stored = repository.byKey(userId, key, pickupId, destinationId);
    if (!stored.sameInput()) {
      throw new ApiError(HttpStatus.CONFLICT, "IDEMPOTENCY_KEY_CONFLICT");
    }
    Ride ride = stored.ride();
    if (created) {
      repository.accepted(ride.id());
    }
    return ride;
  }

  @Transactional(readOnly = true)
  public List<Ride> history(long userId) {
    return repository.history(userId);
  }

  private long stopId(String key) {
    return repository
        .stop(key)
        .orElseThrow(() -> new ApiError(HttpStatus.BAD_REQUEST, "UNKNOWN_STOP"));
  }
}
