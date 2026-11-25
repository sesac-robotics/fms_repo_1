package dev.amo.scenarios.domain;

import dev.amo.scenarios.domain.Scenario.Step;
import java.util.List;

/** Calculates available simulated choices from committed observations. */
public record ReviewProgress(Step next, List<Step> available, Scenario effectiveRoute) {
  /** Resolves the shared checkpoint order and locks movement while a link recovery is pending. */
  public static ReviewProgress at(Scenario initial, List<Step> played) {
    Scenario route =
        played.contains(Step.ROUTE_APPLIED)
            ? Scenario.TAXI_APPLIED
            : played.contains(Step.ROUTE_FAILED) ? Scenario.TAXI_APPLY_FAILED : initial;
    Step next =
        Scenario.stepsFor(route).stream()
            .filter(step -> !played.contains(step))
            .findFirst()
            .orElse(null);
    if (next == null) {
      return new ReviewProgress(null, List.of(), route);
    }
    if (played.contains(Step.LINK_LOST) && !played.contains(Step.LINK_RESTORED)) {
      return only(Step.LINK_RESTORED, route);
    }
    if (played.contains(Step.LINK_RESTORED) && !played.contains(Step.RESUME_APPROVED)) {
      return only(Step.RESUME_APPROVED, route);
    }
    List<Step> available =
        switch (next) {
          case PREPAY ->
              played.contains(Step.PREPAY_DECLINED)
                  ? List.of(next)
                  : List.of(next, Step.PREPAY_DECLINED);
          case STOP_WAIT ->
              played.contains(Step.LINK_LOST) ? List.of(next) : List.of(next, Step.LINK_LOST);
          case ROUTE_APPLIED, ROUTE_FAILED -> List.of(Step.ROUTE_APPLIED, Step.ROUTE_FAILED);
          default -> List.of(next);
        };
    return new ReviewProgress(next, available, route);
  }

  private static ReviewProgress only(Step action, Scenario route) {
    return new ReviewProgress(action, List.of(action), route);
  }
}
