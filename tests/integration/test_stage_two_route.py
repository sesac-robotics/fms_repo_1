"""Exercise SD-09 route updates, validation and stopped re-departure."""

import unittest
from dataclasses import replace

from one_way_trip import Call, TripState
from stage_two_planning import Plan, Rejection, RoadMap
from stage_two_route import Change, ReportKind, RouteFlow, RouteStatus
from stage_two_vehicle import Evidence, Scope

SCOPE = Scope('trip-02', 'assignment-02', 'taxi-02', 2)
CALL = Call('rider-02', 'call-02', 'station', 'museum', 1)
BRIDGE = frozenset({'junction', 'bridge'})
DETOUR = frozenset({'junction', 'detour'})
LINKS = (
    BRIDGE,
    DETOUR,
    frozenset({'bridge', 'museum'}),
    frozenset({'detour', 'cinema'}),
    frozenset({'cinema', 'park'}),
    frozenset({'park', 'museum'}),
)
NODES = frozenset({'isolated', *(node for link in LINKS for node in link)})
OPEN = RoadMap(NODES, frozenset(LINKS))
CHANGE = Change('change', SCOPE, CALL.member, 'park', ('cinema',))
INITIAL = Plan(1, ('junction', 'bridge', 'museum'), (), 'museum')


def evidence(revision: int, sequence: int) -> Evidence:
    """Build correlated IF-04 evidence for the supplied synthetic revision."""
    return Evidence(SCOPE, f'route:{revision}', sequence)


class StageTwoRouteTest(unittest.TestCase):
    """Check applied-only route display, active-route faults, and additional stops."""

    def setUp(self) -> None:
        self.flow = RouteFlow(SCOPE, CALL, 'junction', TripState.DESTINATION, INITIAL)

    def test_sd09_plans_detour_but_displays_only_matched_applied_route(self) -> None:
        roads = replace(OPEN, blocked=frozenset({BRIDGE}))
        plan = self.flow.submit(CHANGE, roads, 40)
        self.assertIsInstance(plan, Plan)
        assert isinstance(plan, Plan)
        self.assertEqual(plan.locations, ('junction', 'detour', 'cinema', 'park'))
        self.assertEqual(plan.waypoints, ('cinema',))
        self.assertEqual(plan.destination, 'park')
        self.assertEqual(self.flow.effective, INITIAL)
        self.assertEqual(
            (self.flow.effective.remaining_m, self.flow.effective.eta_ticks), (200, 4)
        )
        report = evidence(plan.revision, 10)
        self.assertTrue(
            self.flow.receive(ReportKind.ACKNOWLEDGED, report, plan.revision)
        )
        self.assertEqual(self.flow.effective, INITIAL)
        self.assertFalse(self.flow.receive(ReportKind.APPLIED, report, plan.revision))
        self.assertTrue(
            self.flow.receive(
                ReportKind.APPLIED, replace(report, sequence=11), plan.revision
            )
        )
        self.assertEqual(self.flow.effective, plan)
        self.assertEqual(
            (self.flow.effective.remaining_m, self.flow.effective.eta_ticks), (300, 6)
        )
        self.assertIs(self.flow.state, TripState.DESTINATION)
        self.assertEqual(
            (self.flow.initial_call.origin, self.flow.initial_call.destination),
            ('station', 'museum'),
        )
        self.assertEqual(
            self.flow.history, [('planned', 2), ('acknowledged', 2), ('applied', 2)]
        )

    def test_sd09_validates_owner_scope_input_and_duplicate_key(self) -> None:
        invalid = Rejection.INVALID
        self.assertIs(
            self.flow.submit(replace(CHANGE, member='not-owner'), OPEN, 50), invalid
        )
        self.assertIs(self.flow.submit(replace(CHANGE, key=''), OPEN, 50), invalid)
        self.assertIs(
            self.flow.submit(replace(CHANGE, scope=replace(SCOPE, epoch=1)), OPEN, 50),
            invalid,
        )
        self.assertIs(
            self.flow.submit(
                replace(CHANGE, key='absent', destination='absent'), OPEN, 50
            ),
            invalid,
        )
        self.assertIs(
            self.flow.submit(
                replace(CHANGE, key='duplicate-stops', waypoints=('park',)), OPEN, 50
            ),
            invalid,
        )
        plan = self.flow.submit(CHANGE, OPEN, 50)
        self.assertIs(self.flow.submit(CHANGE, OPEN, 5), plan)
        self.assertIs(
            self.flow.submit(replace(CHANGE, destination='museum'), OPEN, 50),
            Rejection.CONFLICT,
        )
        self.assertEqual(self.flow.history.count(('planned', 2)), 1)

    def test_sd09_battery_reserve_and_waypoint_limits_are_separate(self) -> None:
        self.assertIs(self.flow.submit(CHANGE, OPEN, 19), Rejection.WAYPOINT_LIMIT)
        self.assertIs(self.flow.submit(CHANGE, OPEN, 99), Rejection.WAYPOINT_LIMIT)
        self.assertIs(
            self.flow.submit(replace(CHANGE, key='low-range'), OPEN, 20),
            Rejection.ENERGY,
        )
        approved = self.flow.submit(replace(CHANGE, key='sufficient-range'), OPEN, 22)
        self.assertIsInstance(approved, Plan)
        two = replace(CHANGE, key='two', waypoints=('detour', 'cinema'))
        self.assertIs(self.flow.submit(two, OPEN, 29), Rejection.WAYPOINT_LIMIT)
        self.assertIsInstance(
            self.flow.submit(replace(two, key='two-enough'), OPEN, 30), Plan
        )
        self.assertEqual(self.flow.effective, INITIAL)

    def test_sd09_rejected_request_is_distinct_from_blocked_active_route(self) -> None:
        unreachable = replace(CHANGE, key='unreachable', destination='isolated')
        self.assertIs(self.flow.submit(unreachable, OPEN, 40), Rejection.UNREACHABLE)
        self.assertEqual(self.flow.effective, INITIAL)
        self.assertIs(self.flow.road_status(OPEN), RouteStatus.CLEAR)
        single = replace(OPEN, blocked=frozenset({BRIDGE}))
        self.assertIs(self.flow.road_status(single), RouteStatus.REPLAN_REQUIRED)
        no_exit = replace(OPEN, blocked=frozenset({BRIDGE, DETOUR}))
        self.assertIs(self.flow.road_status(no_exit), RouteStatus.SAFE_WAIT)
        self.assertIs(self.flow.road_status(OPEN), RouteStatus.CLEAR)

    def test_sd09_failure_cannot_apply_or_rewrite_original_plan(self) -> None:
        self.assertIsInstance(self.flow.submit(CHANGE, OPEN, 50), Plan)
        self.assertTrue(self.flow.receive(ReportKind.ACKNOWLEDGED, evidence(2, 1), 2))
        self.assertTrue(self.flow.receive(ReportKind.FAILED, evidence(2, 2), 2))
        self.assertFalse(self.flow.receive(ReportKind.APPLIED, evidence(2, 3), 2))
        self.assertEqual(self.flow.effective, INITIAL)
        self.assertIn(('failed', 2), self.flow.history)

    def test_sd09_out_of_order_and_mismatched_route_reports_are_ignored(self) -> None:
        self.assertIsInstance(self.flow.submit(CHANGE, OPEN, 40), Plan)
        newer = replace(CHANGE, key='newer', destination='museum')
        plan = self.flow.submit(newer, OPEN, 40)
        self.assertIsInstance(plan, Plan)
        good = evidence(3, 9)
        for scope in (
            replace(SCOPE, trip='other-trip'),
            replace(SCOPE, assignment='other-assignment'),
            replace(SCOPE, vehicle='other-vehicle'),
            replace(SCOPE, epoch=1),
        ):
            self.assertFalse(
                self.flow.receive(ReportKind.APPLIED, replace(good, scope=scope), 3)
            )
        self.assertFalse(
            self.flow.receive(ReportKind.APPLIED, replace(good, command='route:2'), 3)
        )
        self.assertFalse(self.flow.receive(ReportKind.APPLIED, good, 2))
        self.assertTrue(self.flow.receive(ReportKind.APPLIED, good, 3))
        self.assertFalse(self.flow.receive(ReportKind.ACKNOWLEDGED, evidence(3, 10), 3))
        self.assertFalse(self.flow.receive(ReportKind.APPLIED, evidence(2, 11), 2))
        self.assertEqual(self.flow.effective, plan)

    def test_sd09_stopped_addition_requires_distinct_actual_redeparture(self) -> None:
        previously_applied = Plan(2, ('bridge', 'museum'), (), 'museum')
        stopped = RouteFlow(
            SCOPE, CALL, 'museum', TripState.STOPPED, previously_applied
        )
        self.assertIsNone(stopped.authorize_departure())
        self.assertIs(stopped.submit(CHANGE, OPEN, 40), Rejection.INVALID)
        additional = replace(CHANGE, key='additional', additional_after_stop=True)
        self.assertIs(self.flow.submit(additional, OPEN, 40), Rejection.INVALID)
        self.assertIsInstance(stopped.submit(additional, OPEN, 40), Plan)
        self.assertTrue(stopped.receive(ReportKind.ACKNOWLEDGED, evidence(3, 50), 3))
        self.assertIsNone(stopped.authorize_departure())
        self.assertTrue(stopped.receive(ReportKind.APPLIED, evidence(3, 51), 3))
        self.assertIs(stopped.state, TripState.STOPPED)
        departure = Evidence(SCOPE, 'depart:3', 1)
        self.assertFalse(stopped.observe_departure(departure))
        self.assertEqual(stopped.authorize_departure(), departure.command)
        self.assertFalse(
            stopped.observe_departure(replace(departure, command='depart:2'))
        )
        self.assertFalse(
            stopped.observe_departure(replace(departure, scope=replace(SCOPE, epoch=1)))
        )
        self.assertTrue(stopped.observe_departure(departure))
        self.assertFalse(stopped.observe_departure(departure))
        self.assertIs(stopped.state, TripState.DESTINATION)
        self.assertIn(('departed', 3), stopped.history)
