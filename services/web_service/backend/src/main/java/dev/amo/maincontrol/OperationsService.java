package dev.amo.maincontrol;

import dev.amo.ApiError;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Presents a consistent single-transaction operations snapshot. */
@Service
public class OperationsService {
  private final OperationsRepository repository;
  private final RecordedRouteRepository routes;

  private final boolean demo;

  OperationsService(
      OperationsRepository repository, RecordedRouteRepository routes, Environment environment) {
    this.repository = repository;
    this.routes = routes;
    this.demo = environment.acceptsProfiles(Profiles.of("demo"));
  }

  public boolean ready() {
    try {
      repository.confirmConnection();
      return true;
    } catch (DataAccessException failure) {
      return false;
    }
  }

  /**
   * Returns observed positions from the selected request's most recent started trip.
   *
   * @throws ApiError when the request ID does not exist
   */
  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public RecordedRoute recordedRoute(long requestId) {
    if (requestId <= 0 || !routes.requestExists(requestId)) {
      throw new ApiError(HttpStatus.NOT_FOUND, "REQUEST_NOT_FOUND");
    }
    return RecordedRoute.from(requestId, routes.samples(requestId));
  }

  @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
  public Operations snapshot() {
    return new Operations(
        repository.vehicles(),
        repository.requests(),
        repository.events(),
        repository.tests(),
        demo);
  }
}
