"""Reusable authenticated trip fixtures for the isolated demo gateway tests."""

from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from uuid import uuid4

from demo_http import DemoHttp

BASE = os.environ.get('AMO_DEMO_HTTP', '')


@unittest.skipUnless(BASE, 'requires the isolated local demo servers and PostgreSQL')
class DemoRideCase(unittest.TestCase):
    """Exercise the same authenticated endpoints used by the demo clients."""

    def setUp(self) -> None:
        self.http = DemoHttp(BASE)
        self.passenger = self.http.login('passenger')
        self.admin = self.http.login('admin')
        self.operator = self.http.login('operator')
        self.complete_charge(None)
        status, ride = self.http.send(
            '/api/rides',
            self.passenger,
            {'pickup': 'S1', 'destination': 'S2', 'idempotencyKey': str(uuid4())},
        )
        self.assertEqual(status, 200, ride)
        self.request_id = int(str(ride['id']))
        self.ride = f'/api/rides/{self.request_id}'
        self.observations = f'/api/admin/demo/rides/{ride["id"]}/observe'

    def pay_initial(self) -> dict[str, object]:
        """Verify concurrent initial payment replay and return the accepted quote."""
        status, result = self.http.send(self.ride + '/mock-quote', self.passenger, {})
        self.assertEqual(status, 200, result)
        quote = cast(dict[str, object], result['quote'])
        self.assertEqual(result['paymentStatus'], 'QUOTED')
        payment = {'quoteId': quote['id'], 'key': str(uuid4())}
        with ThreadPoolExecutor(2) as pool:
            first, second = list(
                pool.map(
                    lambda _: self.http.send(
                        self.ride + '/mock-prepayment', self.passenger, payment
                    ),
                    range(2),
                )
            )
        self.assertEqual(first, second)
        self.assertEqual(first[0], 200, first[1])
        self.assertEqual(first[1]['paymentStatus'], 'SUCCEEDED')
        self.assertEqual(
            self.http.send(
                self.ride + '/mock-prepayment',
                self.passenger,
                {**payment, 'quoteId': int(str(quote['id'])) + 1},
            )[1]['code'],
            'FARE_QUOTE_CONFLICT',
        )
        return quote

    def depart(self) -> None:
        """Observe assignment, pickup stop, boarding and departure in order."""
        for step in ('ASSIGN', 'PICKUP_STOP', 'BOARD', 'DEPART'):
            status, result = self.observe(step)
            self.assertEqual(status, 200, result)

    def finish(self) -> dict[str, object]:
        """Record a destination stop and then the corresponding alighting."""
        self.assertEqual(
            self.observe(
                'DESTINATION_STOP', {'distanceMeters': 2.25, 'elapsedSeconds': 17}
            )[0],
            200,
        )
        status, result = self.observe('ALIGHT')
        self.assertEqual(status, 200, result)
        self.complete_charge(self.request_id)
        return cast(dict[str, object], result['receipt'])

    def route(
        self, path: str, payload: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        """Call the staff route replay adapter through the normal IF-02 gateway."""
        return self.http.send(
            self.observations.rsplit('/', 1)[0] + '/route/' + path, self.admin, payload
        )

    def propose(self, destination: str) -> dict[str, object]:
        """Return the newly proposed route or fail on an unexpected response."""
        status, result = self.route('propose', {'destination': destination})
        self.assertEqual(status, 200, result)
        return result

    def accept_change(self, proposal: dict[str, object]) -> dict[str, object]:
        """Accept the proposal once and verify the exact repeat returns the same result."""
        quote = cast(dict[str, object], proposal['quote'])
        payload = {'quoteId': quote['id'], 'key': str(uuid4())}
        endpoint = self.ride + '/mock-change-accept'
        first = self.http.send(endpoint, self.passenger, payload)
        self.assertEqual(first[0], 200, first[1])
        self.assertEqual(self.http.send(endpoint, self.passenger, payload), first)
        return first[1]

    def observe(
        self, step: str, values: dict[str, object] | None = None
    ) -> tuple[int, dict[str, object]]:
        """Submit one authorized fictional event to the staff replay adapter."""
        return self.http.send(
            self.observations, self.admin, {'step': step, **(values or {})}
        )

    def depot(
        self, request_id: int | None, key: str, step: str, battery: float | None = None
    ) -> tuple[int, dict[str, object]]:
        """Submit an initial or trip-scoped synthetic facility report."""
        return self.http.send(
            '/api/admin/demo/depot/observe',
            self.admin,
            {
                'requestId': request_id,
                'key': key,
                'step': step,
                'batteryPercent': battery,
            },
        )

    def complete_charge(self, request_id: int | None) -> None:
        """Replay a complete facility use, including the actual vacating report."""
        if request_id is not None:
            for step in ('RETURN_ORDERED', 'RETURN_ARRIVAL'):
                status, result = self.depot(request_id, step, step)
                self.assertEqual(status, 200, result)
        for step in ('OCCUPIED', 'CHARGE_STARTED'):
            status, result = self.depot(request_id, step, step)
            self.assertEqual(status, 200, result)
        status, result = self.depot(request_id, 'threshold', 'BATTERY_REPORTED', 70)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['phase'], 'WAITING')
        status, result = self.depot(request_id, 'vacated', 'VACATED')
        self.assertEqual(status, 200, result)
        self.assertEqual(result['phase'], 'VACATED')
