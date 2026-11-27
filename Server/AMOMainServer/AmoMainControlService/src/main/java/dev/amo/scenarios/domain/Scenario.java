package dev.amo.scenarios.domain;

import java.util.ArrayList;
import java.util.List;

/** Ordered Taxi review cases based on SD-01–07 and SD-09. */
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
    PREPAY_DECLINED,
    ASSIGN,
    PICKUP_STOP,
    BOARD,
    DEPART,
    STOP_WAIT,
    LINK_LOST,
    LINK_RESTORED,
    RESUME_APPROVED,
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
    RETURN_VACATE
  }

  /** Immutable ordered input and evidence checkpoints for this case. */
  public List<Step> steps() {
    return stepsFor(this);
  }

  static List<Step> stepsFor(Scenario outcome) {
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
                Step.DEPART,
                Step.STOP_WAIT));
    steps.addAll(
        List.of(Step.CHANGE_PROPOSE, Step.CHANGE_ACCEPT, Step.ROUTE_ISSUE, Step.ROUTE_ACK));
    steps.add(outcome == TAXI_APPLIED ? Step.ROUTE_APPLIED : Step.ROUTE_FAILED);
    steps.addAll(
        List.of(
            Step.REDEPART,
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
