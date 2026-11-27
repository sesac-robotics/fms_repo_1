"""Stage 1 operational fixtures and assertions for SD-04, SD-06 and SD-07."""

from unittest import TestCase

from one_way_depot import Billing, DepotState, PaymentResult, Purpose, Slot
from one_way_operations import (
    CommandResult,
    Intersection,
    OperationsView,
    PoseSample,
    Routes,
    Vehicle,
)


class OneWayOperationsTest(TestCase):
    """Exercise the expected decisions using observations supplied by the fixture."""

    def test_sd04_four_distinct_vehicle_poses_in_same_tick(self) -> None:
        view = OperationsView()
        for number in range(1, 5):
            self.assertTrue(
                view.ingest(PoseSample(f'V{number}', 11, number, -number, 0.1))
            )
        same_tick = view.same_tick(11)
        self.assertEqual(set(same_tick), {'V1', 'V2', 'V3', 'V4'})
        self.assertEqual(
            {(pose.x_m, pose.y_m, pose.yaw_rad) for pose in same_tick.values()},
            {(1, -1, 0.1), (2, -2, 0.1), (3, -3, 0.1), (4, -4, 0.1)},
        )
        self.assertFalse(view.ingest(PoseSample('V1', 10, 999, 999, 0.0)))
        self.assertEqual(view.same_tick(11), same_tick)

    def test_sd04_requires_green_empty_exit_and_full_exit_before_next(self) -> None:
        crossing = Intersection()
        crossing.queue('V2', 10)
        crossing.queue('V1', 11)
        self.assertIsNone(crossing.admit(green=False, empty=True, exit_clear=True))
        self.assertIsNone(crossing.admit(green=True, empty=False, exit_clear=True))
        self.assertIsNone(crossing.admit(green=True, empty=True, exit_clear=False))
        self.assertEqual(crossing.admit(green=True, empty=True, exit_clear=True), 'V2')
        self.assertIsNone(crossing.admit(green=True, empty=True, exit_clear=True))
        self.assertFalse(crossing.release('V2', fully_exited=False))
        self.assertFalse(crossing.release('V1', fully_exited=True))
        self.assertEqual(crossing.owner, 'V2')
        self.assertTrue(crossing.release('V2', fully_exited=True))
        self.assertEqual(crossing.admit(green=True, empty=True, exit_clear=True), 'V1')

    def test_sd04_route_detours_waits_and_restores_after_reopening(self) -> None:
        direct, detour = ('a', 'b'), ('c', 'd')
        routes = Routes((direct, detour))
        self.assertEqual(routes.current(), direct)
        routes.blocked.add('b')
        self.assertEqual(routes.current(), detour)
        routes.blocked.add('d')
        self.assertIsNone(routes.current())
        routes.blocked.remove('b')
        self.assertEqual(routes.current(), direct)

    def test_sd04_injected_hazard_uses_vehicle_local_stop(self) -> None:
        vehicle = Vehicle()
        vehicle.local_stop()
        self.assertFalse(vehicle.moving)
        self.assertEqual(vehicle.commands, {})

    def test_sd06_only_selected_car_is_stopped_and_recovery_rechecks_dispatch(
        self,
    ) -> None:
        fleet = {'V1': Vehicle(), 'V2': Vehicle()}
        one, two = fleet['V1'], fleet['V2']
        self.assertFalse(one.issue_stop('stop-A', passenger_status_known=False))
        self.assertTrue(one.issue_stop('stop-A', passenger_status_known=True))
        self.assertTrue(one.record_result('stop-A', 1, CommandResult.RECEIVED))
        self.assertTrue(one.moving)
        self.assertFalse(one.recover(1, depot_arrival=True))
        self.assertTrue(one.record_result('stop-A', 1, CommandResult.COMPLETED))
        self.assertTrue(one.moving)
        self.assertTrue(one.observe_stop('stop-A', 1))
        self.assertFalse(one.moving)
        self.assertTrue(one.excluded)
        self.assertTrue(two.moving)
        self.assertFalse(two.excluded)
        self.assertFalse(one.restore_dispatch(eligible=True))
        self.assertFalse(one.recover(1, depot_arrival=False))
        self.assertTrue(one.recover(1, depot_arrival=True))
        self.assertFalse(one.restore_dispatch(eligible=False))
        self.assertTrue(one.excluded)
        self.assertTrue(one.restore_dispatch(eligible=True))
        self.assertFalse(one.excluded)

    def test_sd06_failures_and_stale_reports_cannot_be_used_as_stop_evidence(
        self,
    ) -> None:
        for result in (CommandResult.FAILED, CommandResult.REJECTED):
            with self.subTest(result=result):
                vehicle = Vehicle()
                self.assertTrue(vehicle.issue_stop('s1', passenger_status_known=True))
                self.assertTrue(vehicle.record_result('s1', 1, result))
                self.assertFalse(vehicle.observe_stop('s1', 1))
                self.assertTrue(vehicle.moving)

        vehicle = Vehicle()
        self.assertTrue(vehicle.issue_stop('s1', passenger_status_known=True))
        vehicle.disconnect()
        self.assertFalse(vehicle.moving)
        self.assertFalse(vehicle.connected)
        self.assertFalse(vehicle.record_result('s1', 1, CommandResult.RECEIVED))
        vehicle.reconnect()
        self.assertTrue(vehicle.connected)
        self.assertEqual(vehicle.epoch, 2)
        self.assertFalse(vehicle.record_result('s1', 1, CommandResult.COMPLETED))
        self.assertFalse(vehicle.observe_stop('s1', 1))
        self.assertEqual(vehicle.commands, {})
        self.assertFalse(vehicle.recover(1, depot_arrival=True))

    def test_sd06_routes_only_the_pre_masked_fixture_asset(self) -> None:
        self.assertEqual(
            OperationsView.display_asset('masked-clip', fixture_is_masked=True),
            'masked-clip',
        )
        self.assertIsNone(
            OperationsView.display_asset('unmasked-control', fixture_is_masked=False)
        )

    def test_sd07_arrival_charge_start_threshold_and_dispatch_are_independent(
        self,
    ) -> None:
        bay = Slot('C1', 'V3', Purpose.CHARGE)
        self.assertFalse(bay.observe('C1', 'V3', 'charge_started'))
        self.assertTrue(bay.observe('C1', 'V3', 'arrival'))
        self.assertEqual(bay.state, DepotState.ARRIVED)
        self.assertFalse(bay.apply_charge('C1', 'V3', 90))
        self.assertFalse(bay.observe('C1', 'V4', 'occupied'))
        self.assertFalse(bay.observe('C1', 'V3', 'charge_started'))
        self.assertTrue(bay.observe('C1', 'V3', 'occupied'))
        self.assertTrue(bay.observe('C1', 'V3', 'charge_started'))
        self.assertFalse(bay.apply_charge('C2', 'V3', 70))
        self.assertFalse(bay.apply_charge('C1', 'V3', 69))
        self.assertEqual(bay.state, DepotState.CHARGING)
        self.assertFalse(bay.eligible(connected=True, battery_pct=69, required_pct=56))
        self.assertTrue(bay.apply_charge('C1', 'V3', 70))
        self.assertEqual(bay.state, DepotState.WAITING)
        self.assertFalse(bay.eligible(connected=True, battery_pct=70, required_pct=56))
        self.assertTrue(bay.observe('C1', 'V3', 'exited'))
        self.assertFalse(bay.eligible(connected=False, battery_pct=70, required_pct=56))
        self.assertFalse(bay.eligible(connected=True, battery_pct=70, required_pct=75))
        self.assertTrue(bay.eligible(connected=True, battery_pct=70, required_pct=56))

    def test_sd05_fare_and_payment_outcomes_are_separate(self) -> None:
        bill = Billing()
        outcome = bill.settle(
            'T1',
            'p1',
            distance_m=120,
            duration_ticks=None,
            method_registered=True,
            payment_succeeds=True,
        )
        self.assertIsNone(outcome.fare_credits)
        self.assertEqual(outcome.result, PaymentResult.WAITING)
        outcome = bill.settle(
            'T1',
            'p1',
            distance_m=120,
            duration_ticks=7,
            method_registered=False,
            payment_succeeds=True,
        )
        self.assertEqual(
            (outcome.fare_credits, outcome.result), (127, PaymentResult.WAITING)
        )
        self.assertEqual(len(bill.payments), 0)
        outcome = bill.settle(
            'T1',
            'p1',
            distance_m=120,
            duration_ticks=7,
            method_registered=True,
            payment_succeeds=False,
        )
        self.assertEqual(
            (outcome.fare_credits, outcome.result), (127, PaymentResult.FAILED)
        )
