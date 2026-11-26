package dev.amo.control.application;

import dev.amo.control.domain.Operations;
import dev.amo.control.domain.RecordedRoute;
import dev.amo.vision.application.VisionObservations;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Presents a consistent single-transaction operations snapshot. */
@Service
public class OperationsService {
  private final OperationsStore repository;
  private final RecordedRouteStore routes;
  private final VisionObservations vision;

  private final boolean demo;
  private final ObjectProvider<ReviewPlaybackSource> review;

  OperationsService(
      OperationsStore repository,
      RecordedRouteStore routes,
      VisionObservations vision,
      Environment environment,
      ObjectProvider<ReviewPlaybackSource> review) {
    this.repository = repository;
    this.routes = routes;
    this.vision = vision;
    this.review = review;
    this.demo = environment.acceptsProfiles(Profiles.of("demo"));
  }

  public boolean ready() {
    return repository.ready();
  }

  /** Returns stored positions for a known request's most recent started trip. */
  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public Optional<RecordedRoute> recordedRoute(long requestId) {
    if (requestId <= 0 || !routes.requestExists(requestId)) {
      return Optional.empty();
    }
    return Optional.of(RecordedRoute.from(requestId, routes.samples(requestId)));
  }

  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public Operations snapshot() {
    var playback = review.getIfAvailable();
    return new Operations(
        repository.vehicles(),
        repository.requests(),
        repository.events(),
        repository.tests(),
        demo,
        playback == null ? null : playback.current(),
        vision.latest());
  }
}
