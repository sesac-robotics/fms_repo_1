"""Exercise SD-08 cancellation ordering and vehicle disposal offline."""

import unittest
from dataclasses import replace

from stage_two_cancellation import CancelFlow, Cancellation, Cause, Phase, ReportKind
from stage_two_vehicle import Evidence, Scope

SCOPE = Scope('trip-01', 'assignment-01', 'taxi-01', 2)
OWNER = 'rider-01'
CANCEL = Cancellation(SCOPE.trip, 'cancel-01', Cause.USER, OWNER)
TIMEOUT = Cancellation(SCOPE.trip, 'timeout-01', Cause.NO_SHOW, None, SCOPE)


def assigned() -> CancelFlow:
    """Start a fresh assigned call en route to the pickup point."""
    return CancelFlow(SCOPE.trip, OWNER, SCOPE, Phase.PICKUP)


def pickup(flow: CancelFlow) -> bool:
    """Inject the matched physical pickup stop; no elapsed minutes are simulated."""
    return flow.observe(
        ReportKind.PICKUP_STOP, Evidence(SCOPE, f'pickup:{SCOPE.trip}', 1)
    )


def cleanup(sequence: int) -> Evidence:
    """Create a cleanup event for the original assigned user's cancellation."""
    return Evidence(SCOPE, f'cleanup:{CANCEL.key}', sequence)


class StageTwoCancellationTest(unittest.TestCase):
    """Observe independent SD-08 intake, motion and assignment outcomes."""

    def test_sd08_queued_owner_cancellation_is_idempotent(self) -> None:
        flow = CancelFlow(SCOPE.trip, OWNER, None, Phase.QUEUED)
        self.assertIsNone(flow.submit(replace(CANCEL, member='different-rider')))
        self.assertIsNone(flow.submit(replace(CANCEL, trip='different-trip')))
        self.assertIsNone(flow.submit(replace(CANCEL, key='')))
        self.assertIs(flow.submit(CANCEL), Phase.CANCELLED)
        self.assertIs(flow.submit(CANCEL), Phase.CANCELLED)
        self.assertIsNone(flow.submit(replace(CANCEL, key='different-cancel')))
        self.assertFalse(flow.assignment_open)
        self.assertEqual(flow.history, ['user_cancel'])

    def test_sd08_pickup_cancel_requires_cleanup_then_return_and_health(self) -> None:
        flow = assigned()
        self.assertIs(flow.submit(CANCEL), Phase.CLEANUP)
        self.assertTrue(flow.observe(ReportKind.ACKNOWLEDGED, cleanup(80)))
        self.assertTrue(flow.assignment_open)
        self.assertFalse(flow.stopped)
        self.assertTrue(flow.observe(ReportKind.ACTUAL_STOP, cleanup(2)))
        self.assertIs(flow.phase, Phase.CLEANUP)
        self.assertTrue(flow.assignment_open)
        self.assertTrue(flow.observe(ReportKind.OLD_WORK_RELEASED, cleanup(3)))
        self.assertIs(flow.phase, Phase.RETURNING)
        self.assertFalse(flow.assignment_open)
        self.assertIs(flow.submit(CANCEL), Phase.RETURNING)
        for link, healthy, pct in [(True, True, 70), (False, True, 70)]:
            self.assertFalse(
                flow.can_dispatch(
                    connected=link, healthy=healthy, battery_pct=pct, required_pct=25
                )
            )
        for connected, healthy, battery_pct, expected in (
            (True, True, 25, True),
            (False, True, 25, False),
            (True, False, 25, False),
            (True, True, 24, False),
        ):
            self.assertEqual(
                flow.can_dispatch(
                    connected=connected,
                    healthy=healthy,
                    battery_pct=battery_pct,
                    required_pct=25,
                    return_interruptible=True,
                ),
                expected,
            )
        arrival = Evidence(SCOPE, f'return:{CANCEL.key}', 4)
        self.assertFalse(flow.observe(ReportKind.RETURN_ARRIVAL, cleanup(4)))
        self.assertTrue(flow.observe(ReportKind.RETURN_ARRIVAL, arrival))
        self.assertIs(flow.phase, Phase.RETURNED)
        for link, healthy, pct in [
            (False, True, 70),
            (True, False, 70),
            (True, True, 24),
        ]:
            self.assertFalse(
                flow.can_dispatch(
                    connected=link, healthy=healthy, battery_pct=pct, required_pct=25
                )
            )
        self.assertTrue(
            flow.can_dispatch(
                connected=True, healthy=True, battery_pct=25, required_pct=25
            )
        )
        self.assertEqual(flow.history.count('assignment_closed'), 1)

    def test_sd08_cleanup_reports_can_arrive_before_ack_and_in_either_order(
        self,
    ) -> None:
        flow = assigned()
        self.assertIs(flow.submit(CANCEL), Phase.CLEANUP)
        self.assertTrue(flow.observe(ReportKind.OLD_WORK_RELEASED, cleanup(3)))
        self.assertTrue(flow.assignment_open)
        self.assertFalse(flow.observe(ReportKind.ACTUAL_STOP, cleanup(2)))
        self.assertFalse(flow.observe(ReportKind.OLD_WORK_RELEASED, cleanup(3)))
        self.assertTrue(flow.observe(ReportKind.ACTUAL_STOP, cleanup(4)))
        self.assertIs(flow.phase, Phase.RETURNING)
        self.assertFalse(flow.observe(ReportKind.ACKNOWLEDGED, cleanup(1)))
        self.assertEqual(flow.history.count('assignment_closed'), 1)

    def test_sd08_cancel_first_blocks_later_boarding(self) -> None:
        flow = assigned()
        self.assertTrue(pickup(flow))
        self.assertIs(flow.submit(CANCEL), Phase.CLEANUP)
        self.assertFalse(flow.confirm_boarding(SCOPE, OWNER))
        self.assertNotIn('boarding_confirmed', flow.history)

    def test_sd08_boarding_first_blocks_cancel_and_no_show(self) -> None:
        flow = assigned()
        self.assertTrue(pickup(flow))
        self.assertFalse(flow.confirm_boarding(SCOPE, 'unknown-member'))
        self.assertFalse(flow.confirm_boarding(replace(SCOPE, epoch=1), OWNER))
        self.assertTrue(flow.confirm_boarding(SCOPE, OWNER))
        self.assertIsNone(flow.submit(CANCEL))
        self.assertIsNone(flow.submit(TIMEOUT))
        self.assertIs(flow.phase, Phase.BOARDED)
        self.assertTrue(flow.assignment_open)

    def test_sd08_no_show_requires_waiting_and_current_assignment_event(self) -> None:
        flow = assigned()
        self.assertIsNone(flow.submit(TIMEOUT))
        self.assertFalse(
            flow.observe(ReportKind.PICKUP_STOP, Evidence(SCOPE, 'wrong-command', 1))
        )
        self.assertTrue(pickup(flow))
        self.assertIsNone(flow.submit(replace(TIMEOUT, timer_scope=None)))
        old = replace(SCOPE, assignment='expired-assignment')
        self.assertIsNone(flow.submit(replace(TIMEOUT, timer_scope=old)))
        self.assertIs(flow.submit(TIMEOUT), Phase.CLEANUP)
        self.assertIs(flow.submit(TIMEOUT), Phase.CLEANUP)
        self.assertIsNone(flow.submit(CANCEL))
        self.assertFalse(flow.confirm_boarding(SCOPE, OWNER))
        report = Evidence(SCOPE, f'cleanup:{TIMEOUT.key}', 2)
        self.assertTrue(flow.observe(ReportKind.ACTUAL_STOP, report))
        release = replace(report, sequence=3)
        self.assertTrue(flow.observe(ReportKind.OLD_WORK_RELEASED, release))
        self.assertEqual(flow.history.count('no_show_timeout'), 1)
        self.assertEqual(flow.history.count('assignment_closed'), 1)

    def test_sd08_cleanup_failure_and_wrong_scope_cannot_free_vehicle(self) -> None:
        flow = assigned()
        self.assertIs(flow.submit(CANCEL), Phase.CLEANUP)
        wrong_scope = (
            replace(SCOPE, trip='other-trip'),
            replace(SCOPE, assignment='old-assignment'),
            replace(SCOPE, vehicle='other-vehicle'),
            replace(SCOPE, epoch=1),
        )
        for scope in wrong_scope:
            evidence = replace(cleanup(2), scope=scope)
            self.assertFalse(flow.observe(ReportKind.ACTUAL_STOP, evidence))
        self.assertFalse(
            flow.observe(ReportKind.ACTUAL_STOP, replace(cleanup(2), command='wrong'))
        )
        self.assertTrue(flow.observe(ReportKind.ACTUAL_STOP, cleanup(2)))
        self.assertTrue(flow.observe(ReportKind.FAILED, cleanup(1)))
        self.assertFalse(flow.observe(ReportKind.OLD_WORK_RELEASED, cleanup(3)))
        self.assertTrue(flow.assignment_open)
        self.assertTrue(flow.cleanup_failed)
        self.assertFalse(
            flow.can_dispatch(
                connected=True, healthy=True, battery_pct=100, required_pct=25
            )
        )
