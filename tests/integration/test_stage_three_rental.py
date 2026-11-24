"""Execute SD-10 Hold timing, parking, return, and billing boundaries."""

import unittest
from dataclasses import replace

from one_way_depot import PaymentResult
from stage_three_rental import HoldRequest, Rental, State
from stage_two_vehicle import Scope

SCOPE = Scope('hold-1', 'assignment-1', 'vehicle-1', 2)
CALL = HoldRequest('member-1', 'pickup', 30)


def moving() -> Rental:
    """Enter the first confirmed moving state at synthetic second 100."""
    rental = Rental(CALL, SCOPE)
    assert rental.set_destination(CALL.owner, 'library', 'leg-1')
    assert rental.vehicle_event(SCOPE, 'leg-1', 'departed', 100)
    return rental


def parking() -> Rental:
    """Reach a destination stop and reserve a matching free parking bay."""
    rental = moving()
    assert rental.vehicle_event(SCOPE, 'leg-1', 'destination_stop', 105)
    assert rental.assign_bay('bay-a', free=True)
    return rental


class HoldTest(unittest.TestCase):
    """Exercise the rental state diagram with explicit synthetic checkpoints."""

    def test_sd10_first_request_positive_duration_and_no_initial_destination(
        self,
    ) -> None:
        for call in (
            replace(CALL, duration=0),
            replace(CALL, duration=-4),
            replace(CALL, pickup=''),
            replace(CALL, destination='lab'),
        ):
            with self.subTest(call=call), self.assertRaises(ValueError):
                Rental(call, SCOPE)
        self.assertIsNone(Rental(CALL, SCOPE).remaining(10_000))

    def test_sd10_countdown_starts_only_on_same_assignment_departure(self) -> None:
        rental = Rental(CALL, SCOPE)
        self.assertFalse(rental.set_destination('other', 'library', 'leg-1'))
        self.assertTrue(rental.set_destination(CALL.owner, 'library', 'leg-1'))
        self.assertIsNone(rental.remaining(120))
        self.assertFalse(rental.expire(120))
        self.assertFalse(
            rental.vehicle_event(replace(SCOPE, epoch=1), 'leg-1', 'departed', 120)
        )
        self.assertFalse(rental.vehicle_event(SCOPE, 'old-command', 'departed', 120))
        self.assertTrue(rental.vehicle_event(SCOPE, 'leg-1', 'departed', 120))
        self.assertFalse(rental.set_destination('other', 'lab', 'leg-2'))
        self.assertTrue(rental.set_destination(CALL.owner, 'lab', 'leg-2'))
        self.assertEqual(rental.destination, 'lab')
        self.assertFalse(rental.vehicle_event(SCOPE, 'leg-1', 'destination_stop', 130))
        self.assertEqual(rental.started_at, 120)
        self.assertEqual(rental.remaining(149), 1)
        self.assertEqual(rental.remaining(150), 0)

    def test_sd10_parking_distinguishes_vehicle_arrival_bay_occupancy_and_exit(
        self,
    ) -> None:
        rental = moving()
        self.assertTrue(rental.vehicle_event(SCOPE, 'leg-1', 'destination_stop', 105))
        self.assertFalse(rental.assign_bay('bay-a', free=False))
        self.assertTrue(rental.assign_bay('bay-a', free=True))
        self.assertFalse(rental.parking_event(SCOPE, 'bay-b', 'arrival'))
        self.assertFalse(rental.parking_event(SCOPE, 'bay-a', 'occupied'))
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'arrival'))
        self.assertIs(rental.state, State.PARKING)
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'occupied'))
        self.assertIs(rental.state, State.PARKED)
        self.assertTrue(rental.set_destination(CALL.owner, 'lab', 'leg-2'))
        self.assertFalse(rental.vehicle_event(SCOPE, 'leg-2', 'departed', 108))
        self.assertFalse(
            rental.parking_event(replace(SCOPE, assignment='old'), 'bay-a', 'exited')
        )
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'exited'))
        self.assertFalse(rental.vehicle_event(SCOPE, 'leg-1', 'departed', 109))
        self.assertTrue(rental.vehicle_event(SCOPE, 'leg-2', 'departed', 110))
        self.assertEqual(rental.scope, SCOPE)
        self.assertEqual(rental.remaining(110), 20)

    def test_sd10_in_motion_expiry_requires_fresh_stop_and_alighting(self) -> None:
        rental = moving()
        self.assertFalse(rental.expire(129))
        self.assertTrue(rental.expire(130))
        self.assertFalse(rental.expire(131))
        self.assertIs(rental.state, State.RETURN_WAIT)
        self.assertEqual(rental.return_reason, 'expired')
        self.assertFalse(rental.confirm_alighting(SCOPE, CALL.owner, 131))
        self.assertFalse(rental.vehicle_event(SCOPE, 'return', 'safely_stopped', 129))
        self.assertTrue(rental.vehicle_event(SCOPE, 'return', 'safely_stopped', 132))
        self.assertFalse(rental.confirm_alighting(SCOPE, 'other', 132))
        self.assertFalse(
            rental.confirm_alighting(replace(SCOPE, trip='old'), CALL.owner, 132)
        )
        self.assertTrue(rental.confirm_alighting(SCOPE, CALL.owner, 133))
        self.assertIs(rental.state, State.RETURNING)

    def test_sd10_parked_manual_return_checks_alighting_and_bay_exit_separately(
        self,
    ) -> None:
        rental = parking()
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'arrival'))
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'occupied'))
        self.assertFalse(rental.request_return('other', 110))
        self.assertTrue(rental.request_return(CALL.owner, 110))
        self.assertEqual(rental.return_reason, 'manual')
        self.assertIs(rental.return_origin, State.PARKED)
        self.assertTrue(rental.confirm_alighting(SCOPE, CALL.owner, 111))
        self.assertIs(rental.state, State.PARKED)
        self.assertTrue(rental.parking_event(SCOPE, 'bay-a', 'exited'))
        self.assertIs(rental.state, State.RETURNING)

    def test_sd10_direct_return_stays_stopped_until_alighting(self) -> None:
        rental = moving()
        self.assertFalse(rental.request_return(CALL.owner, 103))
        self.assertTrue(rental.vehicle_event(SCOPE, 'leg-1', 'destination_stop', 105))
        self.assertTrue(rental.request_return(CALL.owner, 106))
        self.assertIs(rental.return_origin, State.STOPPED)
        self.assertIs(rental.state, State.STOPPED)
        self.assertFalse(rental.vehicle_event(SCOPE, 'return', 'departed', 107))
        self.assertTrue(rental.confirm_alighting(SCOPE, CALL.owner, 107))
        self.assertIs(rental.state, State.RETURNING)

    def test_sd10_returns_then_settles_mock_fare_separately_from_eligibility(
        self,
    ) -> None:
        rental = moving()
        self.assertTrue(rental.expire(135))
        self.assertTrue(rental.vehicle_event(SCOPE, 'return', 'safely_stopped', 136))
        self.assertTrue(rental.confirm_alighting(SCOPE, CALL.owner, 137))
        self.assertIsNone(
            rental.settle('pay', distance_m=40, method=True, succeeds=True)
        )
        self.assertTrue(rental.vehicle_event(SCOPE, 'return', 'garage_arrived', 138))
        waiting = rental.settle('pay', distance_m=40, method=False, succeeds=True)
        assert waiting is not None
        self.assertIs(waiting.result, PaymentResult.WAITING)
        failed = rental.settle('pay', distance_m=40, method=True, succeeds=False)
        assert failed is not None
        self.assertEqual(failed.fare_credits, 70)
        self.assertIs(failed.result, PaymentResult.FAILED)
        self.assertTrue(
            rental.reusable(connected=True, battery_pct=40, required_pct=40)
        )
        self.assertFalse(
            rental.reusable(connected=False, battery_pct=40, required_pct=40)
        )
        self.assertFalse(
            rental.reusable(connected=True, battery_pct=39, required_pct=40)
        )
        self.assertIs(
            rental.settle('pay', distance_m=40, method=True, succeeds=True), failed
        )
        paid = rental.settle('retry', distance_m=40, method=True, succeeds=True)
        assert paid is not None
        self.assertIs(paid.result, PaymentResult.PAID)
