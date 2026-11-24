package dev.amo.scenarios.application;

import dev.amo.maincontrol.RideService;
import dev.amo.replay.application.DepotReplayService;
import dev.amo.replay.application.TripReplayService;
import dev.amo.replay.domain.DepotReplay;
import dev.amo.replay.domain.TripReplay;
import dev.amo.scenarios.application.ScenarioStore.Run;
import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.Scenario.Step;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/** Dispatches an ordered step to the existing intake, trip, fare and depot use cases. */
@Component
@Profile("demo")
class ScenarioSteps {
  private final ScenarioStore store;
  private final RideService rides;
  private final TripReplayService trips;
  private final DepotReplayService depot;
  private final ScenarioFareSteps fares;

  ScenarioSteps(
      ScenarioStore store,
      RideService rides,
      TripReplayService trips,
      DepotReplayService depot,
      ScenarioFareSteps fares) {
    this.store = store;
    this.rides = rides;
    this.trips = trips;
    this.depot = depot;
    this.fares = fares;
  }

  ReviewEvidence execute(Run run, Step step, boolean manual, Instant now) {
    return switch (step) {
      case CALL -> call(run, step, now);
      case QUOTE,
          PREPAY,
          CHANGE_PROPOSE,
          CHANGE_ACCEPT,
          ROUTE_ISSUE,
          ROUTE_ACK,
          ROUTE_APPLIED,
          ROUTE_FAILED ->
          fares.execute(run, step, manual, now);
      case ASSIGN, PICKUP_STOP, BOARD, DEPART, STOP_WAIT, REDEPART, DESTINATION_STOP, ALIGHT ->
          trip(run, step, now);
      case INITIAL_OCCUPY,
          INITIAL_CHARGE,
          INITIAL_READY,
          INITIAL_VACATE,
          RETURN_ORDER,
          RETURN_ARRIVAL,
          RETURN_OCCUPY,
          RETURN_CHARGE,
          RETURN_READY,
          RETURN_VACATE ->
          depot(run, step);
    };
  }

  private ReviewEvidence call(Run run, Step step, Instant now) {
    var ride = rides.accept(run.passengerId(), "S1", "S2", run.key(step), now);
    store.linkRequest(run.id(), ride.id());
    return ReviewEvidence.trip("REQUEST_RECEIVED", ride.receivedAt(), null, ride.status());
  }

  private ReviewEvidence trip(Run run, Step step, Instant now) {
    var operation = TripReplay.Step.valueOf(step.name());
    var totals =
        operation == TripReplay.Step.DESTINATION_STOP ? new TripReplay.Totals(2.25, 17) : null;
    if (step == Step.DESTINATION_STOP || step == Step.ALIGHT) {
      fares.requireEffectiveRoute(run, now);
    }
    var result = trips.observe(run.requestId(), operation, totals);
    if (step == Step.ALIGHT) {
      return fares.settlement(run, result);
    }
    return ReviewEvidence.trip(
        operation.event(), result.observedAt(), result.tripId(), result.status());
  }

  private ReviewEvidence depot(Run run, Step step) {
    var kind =
        switch (step) {
          case INITIAL_OCCUPY, RETURN_OCCUPY -> DepotReplay.Step.OCCUPIED;
          case INITIAL_CHARGE, RETURN_CHARGE -> DepotReplay.Step.CHARGE_STARTED;
          case INITIAL_READY, RETURN_READY -> DepotReplay.Step.BATTERY_REPORTED;
          case INITIAL_VACATE, RETURN_VACATE -> DepotReplay.Step.VACATED;
          case RETURN_ORDER -> DepotReplay.Step.RETURN_ORDERED;
          case RETURN_ARRIVAL -> DepotReplay.Step.RETURN_ARRIVAL;
          default -> throw new IllegalArgumentException("Not a depot step");
        };
    var observation =
        new DepotReplay.Observation(
            kind, run.key(step), kind == DepotReplay.Step.BATTERY_REPORTED ? 70.0 : null);
    var result =
        run.requestId() == null
            ? depot.observeInitial(run.vehicleId(), observation)
            : depot.observe(run.requestId(), observation);
    return ReviewEvidence.depot(
        "DEMO_DEPOT_" + result.step(),
        result.observedAt(),
        result.cycleId(),
        result.phase().name(),
        result.batteryPercent());
  }
}
