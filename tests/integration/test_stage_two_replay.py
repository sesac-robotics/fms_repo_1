"""Connect a dispatched Phase 1 ride to the Phase 2 destination change fixture."""

from unittest import TestCase

from one_way_intake import Intake
from one_way_trip import Call, Candidate, MotionReport, TripState
from stage_two_planning import Plan, Rejection, RoadMap
from stage_two_route import Change, ReportKind, RouteFlow
from stage_two_vehicle import Evidence, Scope


class StageTwoReplayTest(TestCase):
    """Exercise real ordering within a single synthetic call and assignment."""

    def test_sd09_replay_from_call_through_actual_departure_to_change(self) -> None:
        intake = Intake()
        rider = 'synthetic-rider'
        intake.register(rider)
        call = Call(rider, 'initial-call', 'station', 'museum', 10)
        receipt = intake.accept(call, accepted_at=11)
        candidate = Candidate('taxi-1', True, 50, 25, True, True, 3, (1, 2))
        trip = intake.dispatch(receipt, [candidate], epoch=2)
        assert trip is not None
        scope = Scope(
            receipt.trip_id, trip.assignment_id, candidate.vehicle, trip.epoch
        )

        def observe(command: str, event: str) -> bool:
            return trip.observe(
                MotionReport(
                    scope.trip,
                    scope.assignment,
                    scope.vehicle,
                    command,
                    scope.epoch,
                    event,
                )
            )

        self.assertTrue(observe(f'pickup:{scope.trip}', 'pickup_stop'))
        self.assertTrue(
            trip.confirm_boarding(scope.trip, scope.assignment, scope.vehicle, rider)
        )
        self.assertTrue(trip.request_departure('initial-departure'))
        roads = RoadMap(
            frozenset({'junction', 'park', 'museum'}),
            frozenset(
                {frozenset({'junction', 'museum'}), frozenset({'junction', 'park'})}
            ),
        )
        original = Plan(1, ('junction', 'museum'), (), call.destination)
        change = Change('edit', scope, rider, 'park')
        before_departure = RouteFlow(scope, call, 'junction', trip.state, original)
        self.assertIs(
            before_departure.submit(change, roads, candidate.battery_pct),
            Rejection.INVALID,
        )
        self.assertTrue(observe('initial-departure', 'departed'))
        active = RouteFlow(scope, call, 'junction', trip.state, original)
        candidate_route = active.submit(change, roads, candidate.battery_pct)
        self.assertIsInstance(candidate_route, Plan)
        assert isinstance(candidate_route, Plan)
        acceptance = Evidence(scope, 'route:2', 1)
        self.assertTrue(active.receive(ReportKind.ACKNOWLEDGED, acceptance, 2))
        self.assertEqual(active.effective.destination, call.destination)
        self.assertTrue(
            active.receive(ReportKind.APPLIED, Evidence(scope, 'route:2', 2), 2)
        )
        self.assertEqual(active.effective.destination, 'park')
        self.assertEqual(active.initial_call, call)
        self.assertEqual(active.scope, scope)
        self.assertIs(active.state, TripState.DESTINATION)
