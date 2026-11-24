"""Verify SD-01 through SD-05 across the local HTTP gateway and PostgreSQL."""

from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from uuid import uuid4

from demo_http import DemoHttp

BASE = os.environ.get('AMO_DEMO_HTTP', '')


@unittest.skipUnless(BASE, 'requires the isolated local demo servers and PostgreSQL')
class RevisedDemoHttpTest(unittest.TestCase):
    """Exercise the same authenticated endpoints used by the demo clients."""

    def setUp(self) -> None:
        self.http = DemoHttp(BASE)
        self.passenger = self.http.login('passenger')
        self.admin = self.http.login('admin')
        self.operator = self.http.login('operator')
        status, ride = self.http.send(
            '/api/rides',
            self.passenger,
            {'pickup': 'S1', 'destination': 'S2', 'idempotencyKey': str(uuid4())},
        )
        self.assertEqual(status, 200, ride)
        self.ride = f'/api/rides/{ride["id"]}'
        self.observations = f'/api/admin/demo/rides/{ride["id"]}/observe'

    def test_prepayment_replay_dispatch_alight_and_receipt(self) -> None:
        self.assertEqual(self.observe('ASSIGN')[1]['code'], 'FARE_PREPAYMENT_REQUIRED')
        self.assertEqual(self.http.send(self.ride + '/fare', self.operator)[0], 403)
        self.assertEqual(
            self.http.send(self.observations, self.operator, {'step': 'ASSIGN'})[0], 403
        )
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
        for step in ('ASSIGN', 'PICKUP_STOP', 'BOARD', 'DEPART'):
            status, observed = self.observe(step)
            self.assertEqual(status, 200, observed)
        self.assertEqual(self.observe('ALIGHT')[1]['code'], 'DEMO_STEP_OUT_OF_ORDER')
        totals: dict[str, object] = {'distanceMeters': 2.25, 'elapsedSeconds': 17}
        self.assertEqual(self.observe('DESTINATION_STOP', totals)[0], 200)
        self.assertEqual(
            self.observe('DESTINATION_STOP', {**totals, 'elapsedSeconds': 18})[1][
                'code'
            ],
            'DEMO_OBSERVATION_CONFLICT',
        )
        status, closed = self.observe('ALIGHT')
        self.assertEqual(status, 200, closed)
        self.assertEqual((status, closed), self.observe('ALIGHT'))
        self.assertEqual(closed['status'], 'COMPLETED')
        receipt = cast(dict[str, object], closed['receipt'])
        self.assertEqual(receipt['amountMinor'], quote['amountMinor'])
        self.assertEqual(receipt['quoteId'], quote['id'])
        self.assertEqual(
            self.http.send(self.ride + '/fare', self.passenger)[1]['receipt'], receipt
        )

    def observe(
        self, step: str, values: dict[str, object] | None = None
    ) -> tuple[int, dict[str, object]]:
        """Submit one authorized fictional event to the staff replay adapter."""
        return self.http.send(
            self.observations, self.admin, {'step': step, **(values or {})}
        )
