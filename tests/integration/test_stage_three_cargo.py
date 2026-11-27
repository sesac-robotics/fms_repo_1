"""Execute SD-11 Cargo control, hardware evidence, and return boundaries."""

import unittest
from dataclasses import replace

from stage_three_cargo import Cargo, CargoAssignment, CargoEvidence, Event, State
from stage_two_vehicle import Scope

SCOPE = Scope('cargo-1', 'assignment-2', 'vehicle-2', 3)
JOB = CargoAssignment(
    SCOPE, 'job-1', 'cart-1', 'load', 'handoff', 'uncouple', 'garage', 'pickup'
)


def event(kind: Event, site: str, sequence: int) -> CargoEvidence:
    """Build fixture evidence for the active assignment."""
    return CargoEvidence(SCOPE, JOB.job, JOB.cart, site, kind, sequence)


def to_coupled() -> Cargo:
    """Reach physical coupling with separate motion and equipment events."""
    cargo = Cargo(JOB)
    assert cargo.observe('IF-05', event(Event.LOAD_STOP, JOB.origin, 1))
    assert cargo.observe('IF-13', event(Event.LOADED, JOB.origin, 1))
    assert cargo.observe('IF-13', event(Event.COUPLED, JOB.origin, 2))
    return cargo


def pickup_and_board(cargo: Cargo) -> None:
    """Apply the loaded profile, then require common pickup, C03 and physical departure."""
    assert cargo.observe('IF-05', event(Event.LOADED_MODE, JOB.origin, 2))
    assert cargo.observe('IF-05', event(Event.PICKUP_STOP, JOB.pickup, 3))
    assert cargo.observe('mock_c03', event(Event.BOARDING_CONFIRMED, JOB.pickup, 1))
    assert cargo.observe('IF-05', event(Event.DEPARTED, JOB.pickup, 4))


def to_release() -> Cargo:
    """Reach the designated Cargo return stop with the cart attached."""
    cargo = to_coupled()
    pickup_and_board(cargo)
    assert cargo.observe('IF-05', event(Event.HANDOFF_STOP, JOB.destination, 5))
    assert cargo.observe('mock_handoff', event(Event.HANDOFF, JOB.destination, 1))
    assert cargo.observe('IF-05', event(Event.RELEASE_STOP, JOB.release_site, 6))
    return cargo


class CargoTest(unittest.TestCase):
    """Separate confirmed cart handoff from verified reuse of either resource."""

    def test_sd11_request_requires_pickup_delivery_and_designated_release(self) -> None:
        for assignment in (
            replace(JOB, origin=''),
            replace(JOB, pickup=''),
            replace(JOB, destination=''),
            replace(JOB, release_site=''),
            replace(JOB, cart=''),
        ):
            with self.subTest(assignment=assignment), self.assertRaises(ValueError):
                Cargo(assignment)

    def test_sd11_loading_coupling_and_driving_mode_are_distinct(self) -> None:
        cargo = Cargo(JOB)
        left = event(Event.LOADED, JOB.origin, 1)
        self.assertFalse(cargo.observe('IF-13', left))
        self.assertFalse(
            cargo.observe('IF-05', event(Event.LOAD_STOP, JOB.destination, 1))
        )
        self.assertTrue(cargo.observe('IF-05', event(Event.LOAD_STOP, JOB.origin, 1)))
        self.assertTrue(cargo.observe('IF-13', left))
        self.assertIs(cargo.state, State.COUPLING_WAIT)
        coupled = event(Event.COUPLED, JOB.origin, 2)
        self.assertFalse(cargo.observe('IF-04', coupled))
        self.assertTrue(cargo.observe('IF-13', coupled))
        self.assertIs(cargo.state, State.COUPLED)
        mode = event(Event.LOADED_MODE, JOB.origin, 2)
        self.assertFalse(cargo.observe('IF-04', mode))
        self.assertTrue(cargo.observe('IF-05', mode))
        self.assertIs(cargo.state, State.TO_PICKUP)
        self.assertFalse(cargo.observe_distance(SCOPE, 5, 120))
        self.assertFalse(
            cargo.observe('IF-05', event(Event.PICKUP_STOP, JOB.origin, 3))
        )
        self.assertTrue(cargo.observe('IF-05', event(Event.PICKUP_STOP, JOB.pickup, 3)))
        departure = event(Event.DEPARTED, JOB.pickup, 4)
        self.assertFalse(cargo.observe('IF-05', departure))
        confirmation = event(Event.BOARDING_CONFIRMED, JOB.pickup, 1)
        self.assertFalse(cargo.observe('mock_handoff', confirmation))
        self.assertFalse(
            cargo.observe(
                'mock_c03', replace(confirmation, scope=replace(SCOPE, trip='old'))
            )
        )
        self.assertTrue(cargo.observe('mock_c03', confirmation))
        self.assertTrue(cargo.observe('IF-05', departure))
        self.assertIs(cargo.state, State.TRANSPORT)
        self.assertIsNone(cargo.remaining_m)
        self.assertFalse(cargo.observe_distance(replace(SCOPE, epoch=2), 5, 120))
        self.assertFalse(cargo.observe_distance(SCOPE, 5, -1))
        self.assertTrue(cargo.observe_distance(SCOPE, 5, 120))
        self.assertFalse(cargo.observe_distance(SCOPE, 4, 10))
        self.assertEqual(cargo.remaining_m, 120)

    def test_sd11_rejects_other_carts_jobs_places_connections_and_duplicates(
        self,
    ) -> None:
        cargo = to_coupled()
        applied = event(Event.LOADED_MODE, JOB.origin, 2)
        for mismatch in (
            replace(applied, job='other-job'),
            replace(applied, cart='other-cart'),
            replace(applied, site='other-place'),
            replace(applied, scope=replace(SCOPE, vehicle='other')),
            replace(applied, scope=replace(SCOPE, trip='old')),
            replace(applied, scope=replace(SCOPE, epoch=2)),
            replace(applied, sequence=1),
        ):
            self.assertFalse(cargo.observe('IF-05', mismatch))
        self.assertTrue(cargo.observe('IF-05', applied))
        self.assertFalse(cargo.observe('IF-05', applied))

    def test_sd11_recipient_handoff_requires_stop_and_own_confirmation(self) -> None:
        cargo = to_coupled()
        pickup_and_board(cargo)
        handoff = event(Event.HANDOFF, JOB.destination, 1)
        self.assertFalse(cargo.observe('mock_handoff', handoff))
        self.assertTrue(
            cargo.observe('IF-05', event(Event.HANDOFF_STOP, JOB.destination, 5))
        )
        self.assertEqual(cargo.remaining_m, 0)
        self.assertFalse(cargo.observe('IF-09', handoff))
        self.assertTrue(cargo.observe('mock_handoff', handoff))
        self.assertFalse(cargo.cart_reusable())

    def test_sd11_verified_detachment_gates_cart_normal_mode_gates_vehicle(
        self,
    ) -> None:
        cargo = to_release()
        detached = event(Event.DETACHED, JOB.release_site, 3)
        self.assertFalse(
            cargo.observe('IF-13', replace(detached, site=JOB.destination))
        )
        self.assertFalse(cargo.observe('IF-04', detached))
        self.assertTrue(cargo.observe('IF-13', detached))
        self.assertTrue(cargo.cart_reusable())
        self.assertIs(cargo.state, State.RESTORE_WAIT)
        arrival = event(Event.GARAGE_ARRIVAL, JOB.garage, 8)
        self.assertFalse(cargo.observe('IF-05', arrival))
        self.assertTrue(
            cargo.observe('IF-05', event(Event.NORMAL_MODE, JOB.release_site, 7))
        )
        self.assertTrue(cargo.observe('IF-05', arrival))
        for link, battery in ((False, 40), (True, 24)):
            self.assertFalse(
                cargo.vehicle_reusable(
                    connected=link, battery_pct=battery, required_pct=25
                )
            )
        self.assertTrue(
            cargo.vehicle_reusable(connected=True, battery_pct=25, required_pct=25)
        )

    def test_sd11_missing_or_failed_detachment_blocks_normal_close_and_reuse(
        self,
    ) -> None:
        cargo = to_release()
        mode = event(Event.NORMAL_MODE, JOB.release_site, 7)
        self.assertFalse(cargo.observe('IF-05', mode))
        self.assertTrue(
            cargo.observe('IF-13', event(Event.RELEASE_FAILED, JOB.release_site, 3))
        )
        self.assertFalse(
            cargo.observe('IF-13', event(Event.DETACHED, JOB.release_site, 4))
        )
        self.assertFalse(cargo.observe('IF-05', mode))
        self.assertIs(cargo.state, State.RELEASE_BLOCKED)
        self.assertFalse(cargo.cart_reusable())
        self.assertFalse(
            cargo.vehicle_reusable(connected=True, battery_pct=100, required_pct=25)
        )

    def test_sd11_cancellation_before_and_after_coupling_stays_on_hold(self) -> None:
        for cargo in (Cargo(JOB), to_coupled()):
            with self.subTest(state=cargo.state):
                previous = cargo.state
                self.assertFalse(cargo.request_cancellation(replace(SCOPE, trip='old')))
                self.assertTrue(cargo.request_cancellation(SCOPE))
                self.assertTrue(cargo.held_for_review)
                self.assertIs(cargo.state, previous)
                self.assertFalse(
                    cargo.observe('IF-05', event(Event.LOADED_MODE, JOB.origin, 2))
                )
                self.assertFalse(cargo.cart_reusable())
