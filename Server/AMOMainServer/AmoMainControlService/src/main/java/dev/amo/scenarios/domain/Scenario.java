package dev.amo.scenarios.domain;

import java.util.ArrayList;
import java.util.List;

/** Ordered Taxi review cases based on SD-01–05, SD-07 and SD-09. */
public enum Scenario {
  TAXI_APPLIED,
  TAXI_APPLY_FAILED;

  /** Stable step identities shared by the scenario catalog, storage and the desktop client. */
  public enum Step {
    INITIAL_OCCUPY,
    INITIAL_CHARGE,
    INITIAL_READY,
    INITIAL_VACATE,
    CALL,
    QUOTE,
    PREPAY,
    ASSIGN,
    PICKUP_STOP,
    BOARD,
    DEPART,
    STOP_WAIT,
    CHANGE_PROPOSE,
    CHANGE_ACCEPT,
    ROUTE_ISSUE,
    ROUTE_ACK,
    ROUTE_APPLIED,
    ROUTE_FAILED,
    REDEPART,
    DESTINATION_STOP,
    ALIGHT,
    RETURN_ORDER,
    RETURN_ARRIVAL,
    RETURN_OCCUPY,
    RETURN_CHARGE,
    RETURN_READY,
    RETURN_VACATE;

    /** These passenger actions can either be replayed or verified after manual Android input. */
    public boolean acceptsManualInput() {
      return this == QUOTE || this == PREPAY || this == CHANGE_PROPOSE || this == CHANGE_ACCEPT;
    }
  }

  /** Immutable ordered input and evidence checkpoints for this case. */
  public List<Step> steps() {
    var steps =
        new ArrayList<>(
            List.of(
                Step.INITIAL_OCCUPY,
                Step.INITIAL_CHARGE,
                Step.INITIAL_READY,
                Step.INITIAL_VACATE,
                Step.CALL,
                Step.QUOTE,
                Step.PREPAY,
                Step.ASSIGN,
                Step.PICKUP_STOP,
                Step.BOARD,
                Step.DEPART));
    if (this == TAXI_APPLIED) {
      steps.add(Step.STOP_WAIT);
    }
    steps.addAll(
        List.of(Step.CHANGE_PROPOSE, Step.CHANGE_ACCEPT, Step.ROUTE_ISSUE, Step.ROUTE_ACK));
    if (this == TAXI_APPLIED) {
      steps.addAll(List.of(Step.ROUTE_APPLIED, Step.REDEPART));
    } else {
      steps.add(Step.ROUTE_FAILED);
    }
    steps.addAll(
        List.of(
            Step.DESTINATION_STOP,
            Step.ALIGHT,
            Step.RETURN_ORDER,
            Step.RETURN_ARRIVAL,
            Step.RETURN_OCCUPY,
            Step.RETURN_CHARGE,
            Step.RETURN_READY,
            Step.RETURN_VACATE));
    return List.copyOf(steps);
  }

  /** Expected effective stop after the route report, before destination stop and settlement. */
  public String effectiveDestination() {
    return this == TAXI_APPLIED ? "S4" : "S2";
  }
}
