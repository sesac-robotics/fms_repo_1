"""Stage 1 one-way taxi replay for SD-01, SD-02, SD-03 and SD-05."""

from dataclasses import replace
from unittest import TestCase

from one_way_depot import Billing, DepotState, PaymentResult, Purpose, Slot
from one_way_intake import Intake
from one_way_trip import Call, Candidate, MotionReport, Trip, TripState


def _ready() -> Candidate:
    return Candidate('V2', True, 72, 58, True, True, 30, (12, 5))


class OneWayTripTest(TestCase):
    """Run the trip against local synthetic inputs."""

    def setUp(self) -> None:
        """Set up the reusable one-way request."""
        self.intake = Intake()
        self.intake.register('member-1')
        self.call = Call('member-1', 'call-1', 'north', 'west', 100)

    def _start(self) -> Trip:
        receipt = self.intake.accept(self.call, accepted_at=105)
        trip = self.intake.dispatch(receipt, [_ready()], epoch=1)
        if trip is None:
            self.fail('mock dispatch did not return a trip')
        return trip

    @staticmethod
    def _report(trip: Trip, command: str, event: str) -> MotionReport:
        return MotionReport(
            trip.receipt.trip_id,
            trip.assignment_id,
            trip.candidate.vehicle,
            command,
            1,
            event,
        )

    def test_sd01_replay_preserves_first_acceptance(self) -> None:
        receipt = self.intake.accept(self.call, accepted_at=105)
        self.assertEqual((receipt.call.requested_at, receipt.accepted_at), (100, 105))
        self.assertEqual(self.intake.accept(self.call, accepted_at=115), receipt)
        self.assertEqual(len(self.intake.receipts), 1)

    def test_sd01_rejects_unknown_incomplete_and_conflicting_requests(self) -> None:
        with self.assertRaisesRegex(ValueError, 'unknown member'):
            self.intake.accept(replace(self.call, member='unknown'), accepted_at=105)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.intake.accept(replace(self.call, destination=''), accepted_at=105)
        with self.assertRaisesRegex(ValueError, 'intake precedes'):
            self.intake.accept(self.call, accepted_at=99)
        self.intake.accept(self.call, accepted_at=105)
        with self.assertRaisesRegex(ValueError, 'key collision'):
            self.intake.accept(
                replace(self.call, destination='changed'), accepted_at=110
            )

    def test_sd02_dispatch_filters_ineligible_candidates_and_preserves_pickup(
        self,
    ) -> None:
        receipt = self.intake.accept(self.call, accepted_at=105)
        ready = _ready()
        unavailable = [
            replace(ready, vehicle='V1', connected=False, eta=1),
            replace(ready, vehicle='V3', battery_pct=57, eta=1),
            replace(ready, vehicle='V4', route_open=False, eta=1),
            replace(ready, vehicle='V5', available=False, eta=1),
        ]
        self.assertIsNone(self.intake.dispatch(receipt, unavailable, epoch=1))
        self.assertEqual(self.intake.waiting, {'T1': 'no_eligible_vehicle'})
        trip = self.intake.dispatch(receipt, [*unavailable, ready], epoch=1)
        if trip is None:
            self.fail('expected an eligible mock vehicle')
        self.assertEqual(
            (trip.candidate.vehicle, trip.candidate.eta, trip.candidate.position_m),
            ('V2', 30, (12, 5)),
        )
        event = self._report(trip, 'pickup:T1', 'pickup_stop')
        self.assertFalse(trip.observe(replace(event, vehicle='V1')))
        self.assertEqual(trip.state, TripState.PICKUP)
        self.assertTrue(trip.observe(event))
        self.assertEqual(trip.state, TripState.BOARDING)
        self.assertFalse(trip.observe(event))
        self.assertIs(self.intake.dispatch(receipt, unavailable, epoch=1), trip)
        self.assertEqual(self.intake.waiting, {})
        second = self.intake.accept(replace(self.call, key='call-2'), accepted_at=110)
        self.assertIsNone(self.intake.dispatch(second, [ready], epoch=1))

    def test_sd03_confirmation_and_actual_departure_are_separate(self) -> None:
        trip = self._start()
        self.assertTrue(trip.observe(self._report(trip, 'pickup:T1', 'pickup_stop')))
        self.assertFalse(trip.request_departure('D1'))
        self.assertFalse(trip.confirm_boarding('old-trip', 'A1', 'V2', 'member-1'))
        self.assertFalse(trip.confirm_boarding('T1', 'A1', 'V2', 'other-member'))
        self.assertFalse(
            trip.confirm_boarding('T1', 'old-assignment', 'V2', 'member-1')
        )
        self.assertFalse(trip.request_departure('D1'))
        self.assertTrue(trip.confirm_boarding('T1', 'A1', 'V2', 'member-1'))
        self.assertTrue(trip.request_departure('D1'))
        self.assertFalse(trip.request_departure('D2'))
        self.assertEqual(trip.state, TripState.BOARDING)
        event = self._report(trip, 'D1', 'departed')
        for mismatch in (
            replace(event, trip_id='old-trip'),
            replace(event, assignment_id='old-assignment'),
            replace(event, command='D2'),
            replace(event, epoch=0),
        ):
            self.assertFalse(trip.observe(mismatch))
        self.assertEqual(trip.state, TripState.BOARDING)
        self.assertTrue(trip.observe(event))
        self.assertEqual(trip.state, TripState.DESTINATION)
        self.assertFalse(trip.observe(event))

    def test_sd05_replay_closes_trip_pays_and_releases_parking_after_exit(self) -> None:
        trip = self._start()
        self.assertTrue(trip.observe(self._report(trip, 'pickup:T1', 'pickup_stop')))
        self.assertTrue(trip.confirm_boarding('T1', 'A1', 'V2', 'member-1'))
        self.assertTrue(trip.request_departure('D1'))
        self.assertTrue(trip.observe(self._report(trip, 'D1', 'departed')))
        self.assertFalse(trip.close_ride('member-1', alighted=True))
        self.assertTrue(trip.observe(self._report(trip, 'D1', 'destination_stop')))
        self.assertEqual(trip.state, TripState.STOPPED)
        self.assertFalse(trip.close_ride('member-1', alighted=False))
        self.assertFalse(trip.close_ride('wrong-member', alighted=True))
        self.assertTrue(trip.close_ride('member-1', alighted=True))
        self.assertEqual(trip.state, TripState.RETURNING)
        self.assertEqual(
            trip.events, ['pickup_stop', 'departed', 'destination_stop', 'alighted']
        )

        bill = Billing()
        paid = bill.settle(
            'T1',
            'payment-1',
            distance_m=120,
            duration_ticks=7,
            method_registered=True,
            payment_succeeds=True,
        )
        self.assertEqual((paid.fare_credits, paid.result), (127, PaymentResult.PAID))
        retry = bill.settle(
            'T1',
            'payment-1',
            distance_m=120,
            duration_ticks=7,
            method_registered=True,
            payment_succeeds=False,
        )
        self.assertEqual(retry, paid)
        self.assertEqual(len(bill.payments), 1)

        bay = Slot('P1', trip.candidate.vehicle, Purpose.PARK)
        self.assertTrue(bay.observe('P1', 'V2', 'arrival'))
        self.assertEqual(bay.state, DepotState.ARRIVED)
        self.assertFalse(bay.observe('P2', 'V2', 'occupied'))
        self.assertFalse(bay.observe('P1', 'V2', 'charge_started'))
        self.assertFalse(bay.observe('P1', 'V2', 'exited'))
        self.assertTrue(bay.observe('P1', 'V2', 'occupied'))
        self.assertFalse(bay.eligible(connected=True, battery_pct=72, required_pct=58))
        self.assertTrue(bay.observe('P1', 'V2', 'exited'))
        self.assertTrue(bay.eligible(connected=True, battery_pct=72, required_pct=58))
