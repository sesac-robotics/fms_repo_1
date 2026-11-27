"""Replay SD-01 through SD-07 over one shared set of synthetic identities."""

from unittest import TestCase

from one_way_depot import Billing, DepotState, PaymentResult, Purpose, Slot
from one_way_intake import Intake
from one_way_operations import (
    CommandResult,
    Intersection,
    OperationsView,
    PoseSample,
    Routes,
    Vehicle,
)
from one_way_trip import Call, Candidate, MotionReport, TripState


class OneWayCompleteReplayTest(TestCase):
    """Verify that one trip can reach depot waiting through the mock boundaries."""

    def test_sd01_to_sd07_one_trip_through_charging_wait(self) -> None:
        """Replay valid reports with matching trip, assignment, and vehicle IDs."""
        routes = Routes((('pickup', 'crossing', 'destination'),))
        intake = Intake()
        intake.register('passenger')
        call = Call('passenger', 'request', 'pickup', 'destination', 1)
        receipt = intake.accept(call, accepted_at=2)
        self.assertEqual(intake.accept(call, accepted_at=9), receipt)
        self.assertEqual((receipt.call.requested_at, receipt.accepted_at), (1, 2))

        candidate = Candidate(
            vehicle='taxi-1',
            connected=True,
            battery_pct=75,
            required_pct=65,
            route_open=routes.current() is not None,
            available=True,
            eta=3,
            position_m=(1, 2),
        )
        trip = intake.dispatch(receipt, [candidate], epoch=1)
        assert trip is not None
        self.assertEqual(trip.state, TripState.PICKUP)
        vehicle_id = trip.candidate.vehicle

        def observe(command: str, event: str) -> None:
            self.assertTrue(
                trip.observe(
                    MotionReport(
                        receipt.trip_id,
                        trip.assignment_id,
                        vehicle_id,
                        command,
                        trip.epoch,
                        event,
                    )
                )
            )

        observe(f'pickup:{receipt.trip_id}', 'pickup_stop')
        self.assertEqual(trip.state, TripState.BOARDING)
        self.assertFalse(trip.request_departure('depart'))
        self.assertTrue(
            trip.confirm_boarding(
                receipt.trip_id, trip.assignment_id, vehicle_id, call.member
            )
        )
        self.assertTrue(trip.request_departure('depart'))
        self.assertEqual(trip.state, TripState.BOARDING)
        observe('depart', 'departed')
        self.assertEqual(trip.state, TripState.DESTINATION)

        view = OperationsView()
        self.assertTrue(view.ingest(PoseSample(vehicle_id, 6, 3, 5, 0.2)))
        self.assertIn(vehicle_id, view.same_tick(6))
        crossing = Intersection()
        crossing.queue(vehicle_id, 6)
        crossing.queue('other-taxi', 7)
        self.assertEqual(
            crossing.admit(green=True, empty=True, exit_clear=True), vehicle_id
        )
        self.assertTrue(crossing.release(vehicle_id, fully_exited=True))

        observe('depart', 'destination_stop')
        self.assertEqual(trip.state, TripState.STOPPED)
        self.assertTrue(trip.close_ride(call.member, alighted=True))
        self.assertEqual(trip.state, TripState.RETURNING)
        payment = Billing().settle(
            receipt.trip_id,
            'payment',
            distance_m=16,
            duration_ticks=12,
            method_registered=True,
            payment_succeeds=True,
        )
        self.assertEqual(payment.result, PaymentResult.PAID)

        vehicle = Vehicle()
        self.assertTrue(vehicle.issue_stop('stop', passenger_status_known=True))
        self.assertTrue(
            vehicle.record_result('stop', trip.epoch, CommandResult.RECEIVED)
        )
        self.assertTrue(vehicle.moving)
        self.assertTrue(vehicle.observe_stop('stop', trip.epoch))
        self.assertFalse(vehicle.moving)

        slot = Slot('C1', vehicle_id, Purpose.CHARGE)
        self.assertTrue(slot.observe('C1', vehicle_id, 'arrival'))
        self.assertEqual(slot.state, DepotState.ARRIVED)
        self.assertTrue(slot.observe('C1', vehicle_id, 'occupied'))
        self.assertTrue(slot.observe('C1', vehicle_id, 'charge_started'))
        self.assertFalse(slot.apply_charge('C1', vehicle_id, 69))
        self.assertTrue(slot.apply_charge('C1', vehicle_id, 70))
        self.assertEqual(slot.state, DepotState.WAITING)
        self.assertFalse(slot.eligible(connected=True, battery_pct=70, required_pct=65))
        self.assertTrue(slot.observe('C1', vehicle_id, 'exited'))
        self.assertTrue(slot.eligible(connected=True, battery_pct=70, required_pct=65))
