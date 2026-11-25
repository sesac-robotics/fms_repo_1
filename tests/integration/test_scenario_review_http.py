"""Verify the ordered Taxi stage runner against the demo servers and PostgreSQL."""

from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid4

from demo_http import DemoHttp

ROOT = '/api/admin/demo/scenarios'
ORIGIN = os.environ.get('AMO_DEMO_HTTP', '')


@unittest.skipUnless(ORIGIN, 'requires isolated demo servers and PostgreSQL')
class ScenarioReviewHttpTest(unittest.TestCase):
    """Exercise the same run and step API used by the Admin tab."""

    def setUp(self) -> None:
        self.http = DemoHttp(ORIGIN)
        self.admin = self.http.login('admin')
        self.passenger = self.http.login('passenger')

    def test_applied_route_keeps_acknowledgement_and_redeparture_separate(self) -> None:
        run = self.start('TAXI_APPLIED')
        rejected = self.http.send(
            f'{ROOT}/runs/{run["id"]}/steps/ASSIGN', self.admin, {}
        )
        self.assertEqual(rejected, (409, {'code': 'SCENARIO_STEP_OUT_OF_ORDER'}))
        with ThreadPoolExecutor(2) as pool:
            first, second = list(
                pool.map(lambda _: self.play(run, 'INITIAL_OCCUPY'), range(2))
            )
        self.assertEqual(first, second)
        self.assertEqual(len(first['completed']), 1)
        acknowledged = self.through(first, 'ROUTE_ACK')
        self.assertEqual(
            self.evidence(acknowledged, 'ROUTE_ACK')['status'], 'ACKNOWLEDGED'
        )
        self.assert_effective(acknowledged, 'S2', None)
        applied = self.play(acknowledged, 'ROUTE_APPLIED')
        checkpoint = self.evidence(applied, 'ROUTE_APPLIED')
        self.assertEqual(checkpoint['status'], 'APPLIED')
        self.assertEqual(applied['nextStep'], 'REDEPART')
        self.assert_effective(applied, 'S4', checkpoint['revisionId'])
        finished = self.finish(applied)
        final = self.evidence(finished, 'ALIGHT')
        self.assertEqual(final['quoteId'], checkpoint['quoteId'])
        self.assertEqual(final['amountMinor'], checkpoint['amountMinor'])
        self.assertEqual(self.evidence(finished, 'RETURN_READY')['batteryPercent'], 70)
        self.assertEqual(self.evidence(finished, 'RETURN_VACATE')['status'], 'VACATED')
        self.assertEqual(self.play(finished, 'ALIGHT'), finished)

    def test_map_positions_and_current_stage_over_if03(self) -> None:
        run = self.through(self.start('TAXI_APPLIED'), 'PICKUP_STOP')
        first = self.vehicle_snapshot(run, 'PICKUP_STOP')
        self.assertEqual((first['xM'], first['yM']), (0.516, 0.913))
        moving = self.play(self.play(run, 'BOARD'), 'DEPART')
        second = self.vehicle_snapshot(moving, 'DEPART')
        self.assertNotEqual(first['xM'], second['xM'])

    def vehicle_snapshot(self, run: dict[str, Any], step: str) -> dict[str, object]:
        """Read the current review stage and map point over the fleet interface."""
        port = os.environ.get('AMO_DEMO_IF03_PORT')
        status, snap = (
            self.http.fms_snapshot(int(port), self.admin)
            if port
            else self.http.send('/api/operations', self.admin)
        )
        self.assertEqual(status, 200, snap)
        events = cast(list[dict[str, object]], snap['events'])
        stage = next(
            e
            for e in events
            if e['vehicle'] == run['vehicleNumber']
            and str(e['type']).startswith('DEMO_REVIEW_')
        )
        self.assertEqual(stage['type'], f'DEMO_REVIEW_{step}')
        return next(
            v
            for v in cast(list[dict[str, object]], snap['vehicles'])
            if v['vehicleNo'] == run['vehicleNumber']
        )

    def test_paid_failure_preserves_evidence(self) -> None:
        original = self.through(self.start('TAXI_APPLY_FAILED'), 'ROUTE_ACK')
        failed = self.play(original, 'ROUTE_FAILED')
        result = self.evidence(failed, 'ROUTE_FAILED')
        self.assertEqual(result['paymentStatus'], 'SUCCEEDED')
        self.assertGreater(result['deltaMinor'], 0)
        self.assertEqual(result['status'], 'FAILED')
        self.assert_effective(failed, 'S2', None)
        final = self.evidence(self.finish(failed), 'ALIGHT')
        initial = self.evidence(failed, 'QUOTE')
        self.assertEqual(
            (final['quoteId'], final['amountMinor']),
            (initial['quoteId'], initial['amountMinor']),
        )

    def test_manual_passenger_evidence_and_admin_boundary(self) -> None:
        operator = self.http.login('operator')
        self.assertEqual(self.http.send(ROOT, operator)[0], 403)
        self.assertEqual(self.http.send(ROOT, self.passenger)[0], 403)
        run = self.through(self.start('TAXI_APPLIED'), 'CALL')
        pending = f'{ROOT}/runs/{run["id"]}/steps/QUOTE'
        self.assertEqual(
            self.http.send(pending, self.admin, {'manual': True}),
            (409, {'code': 'SCENARIO_WAITING_ANDROID'}),
        )
        ride = f'/api/rides/{run["requestId"]}'
        status, quote = self.http.send(ride + '/mock-quote', self.passenger, {})
        self.assertEqual(status, 200, quote)
        after_quote = self.play(run, 'QUOTE', manual=True)
        prepay = f'{ROOT}/runs/{run["id"]}/steps/PREPAY'
        self.assertEqual(
            self.http.send(prepay, self.admin, {'manual': True}),
            (409, {'code': 'SCENARIO_WAITING_ANDROID'}),
        )
        terms = cast(dict[str, object], quote['quote'])
        status, paid = self.http.send(
            ride + '/mock-prepayment',
            self.passenger,
            {'quoteId': terms['id'], 'key': str(uuid4())},
        )
        self.assertEqual(status, 200, paid)
        recorded = self.play(after_quote, 'PREPAY', manual=True)
        self.assertEqual(
            self.evidence(recorded, 'PREPAY')['paymentStatus'], 'SUCCEEDED'
        )
        status, catalog = self.http.send(ROOT, self.admin)
        self.assertEqual(status, 200, catalog)
        self.assertEqual(catalog['latest'], recorded)

    def start(self, plan: str) -> dict[str, Any]:
        """Start a review on the shared fixture, retrying the same run ID."""
        payload: dict[str, object] = {'plan': plan, 'id': str(uuid4())}
        status, run = self.http.send(ROOT + '/runs', self.admin, payload)
        self.assertEqual(status, 200, run)
        self.assertEqual(
            self.http.send(ROOT + '/runs', self.admin, payload), (200, run)
        )
        return run

    def play(
        self, run: dict[str, Any], step: str, *, manual: bool = False
    ) -> dict[str, Any]:
        """Submit one ordered checkpoint and read committed evidence."""
        status, result = self.http.send(
            f'{ROOT}/runs/{run["id"]}/steps/{step}', self.admin, {'manual': manual}
        )
        self.assertEqual(status, 200, (step, result))
        return result

    def through(self, run: dict[str, Any], stop: str) -> dict[str, Any]:
        """Play each remaining prerequisite and stop after the requested checkpoint."""
        while (step := run['nextStep']) is not None:
            run = self.play(run, step)
            if step == stop:
                return run
        self.fail(f'Checkpoint missing: {stop}')

    def finish(self, run: dict[str, Any]) -> dict[str, Any]:
        """Complete the return and close the local facility cycle."""
        return self.through(run, 'RETURN_VACATE')

    def evidence(self, run: dict[str, Any], step: str) -> dict[str, Any]:
        """Read the evidence recorded for a checkpoint, failing if absent."""
        return cast(
            dict[str, Any],
            next(item['evidence'] for item in run['completed'] if item['step'] == step),
        )

    def assert_effective(
        self, run: dict[str, Any], stop: str, revision: object
    ) -> None:
        """Read the FMS snapshot over development IF-03 and compare effective route."""
        port = os.environ.get('AMO_DEMO_IF03_PORT')
        status, snapshot = (
            self.http.fms_snapshot(int(port), self.admin)
            if port
            else self.http.send('/api/operations', self.admin)
        )
        self.assertEqual(status, 200, snapshot)
        request = next(
            row
            for row in cast(list[dict[str, object]], snapshot['requests'])
            if row['id'] == run['requestId']
        )
        self.assertEqual(request['effectiveDestination'], stop)
        self.assertEqual(request['appliedRevisionId'], revision)
