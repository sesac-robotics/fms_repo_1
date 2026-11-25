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
        self.assertEqual(
            self.evidence(acknowledged, 'ROUTE_ACK')['effectiveDestination'], 'S2'
        )
        self.assert_not_in_operations(acknowledged)
        applied = self.play(acknowledged, 'ROUTE_APPLIED')
        checkpoint = self.evidence(applied, 'ROUTE_APPLIED')
        self.assertEqual(checkpoint['status'], 'APPLIED')
        self.assertEqual(applied['nextStep'], 'REDEPART')
        self.assertEqual(checkpoint['effectiveDestination'], 'S4')
        self.assertIsNotNone(checkpoint['revisionId'])
        finished = self.finish(applied)
        final = self.evidence(finished, 'ALIGHT')
        self.assertEqual(final['quoteId'], checkpoint['quoteId'])
        self.assertEqual(final['amountMinor'], checkpoint['amountMinor'])
        self.assertEqual(self.evidence(finished, 'RETURN_READY')['batteryPercent'], 70)
        self.assertEqual(self.evidence(finished, 'RETURN_VACATE')['status'], 'VACATED')
        self.assertEqual(self.play(finished, 'ALIGHT'), finished)

    def test_current_review_checkpoints_over_if03(self) -> None:
        run = self.start('TAXI_APPLIED')
        self.assertEqual(self.playback(run)['checkpoints'], [])
        pickup = self.through(run, 'PICKUP_STOP')
        first = self.playback(pickup)
        self.assertEqual(first['checkpoints'][-1]['step'], 'PICKUP_STOP')
        moving = self.play(self.play(pickup, 'BOARD'), 'DEPART')
        second = self.playback(moving)
        self.assertEqual(second['checkpoints'][-1]['step'], 'DEPART')
        self.assertNotEqual(first['schematicPoint'], second['schematicPoint'])

    def test_paid_failure_preserves_evidence(self) -> None:
        original = self.through(self.start('TAXI_APPLY_FAILED'), 'ROUTE_ACK')
        failed = self.play(original, 'ROUTE_FAILED')
        result = self.evidence(failed, 'ROUTE_FAILED')
        self.assertEqual(result['paymentStatus'], 'SUCCEEDED')
        self.assertGreater(result['deltaMinor'], 0)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['effectiveDestination'], 'S2')
        final = self.evidence(self.finish(failed), 'ALIGHT')
        initial = self.evidence(failed, 'QUOTE')
        self.assertEqual(
            (final['quoteId'], final['amountMinor']),
            (initial['quoteId'], initial['amountMinor']),
        )

    def test_admin_boundary_and_passenger_isolation(self) -> None:
        operator = self.http.login('operator')
        self.assertEqual(self.http.send(ROOT, operator)[0], 403)
        self.assertEqual(self.http.send(ROOT, self.passenger)[0], 403)
        self.assertEqual(self.http.send(ROOT + '/history/reset', operator, {})[0], 403)
        run = self.through(self.start('TAXI_APPLIED'), 'CALL')
        self.assertEqual(
            self.http.send(
                f'{ROOT}/runs/{run["id"]}/steps/QUOTE', self.admin, {'manual': True}
            ),
            (409, {'code': 'SCENARIO_MANUAL_INPUT_UNSUPPORTED'}),
        )
        ride = f'/api/rides/{run["requestId"]}'
        self.assertEqual(
            self.http.send(ride + '/mock-quote', self.passenger, {})[0], 404
        )
        self.assert_not_in_operations(run)

    def test_choose_payment_recovery_and_alternative_route(self) -> None:
        quoted = self.through(self.start('TAXI_APPLIED'), 'QUOTE')
        declined = self.play(quoted, 'PREPAY_DECLINED')
        self.assertEqual(
            self.evidence(declined, 'PREPAY_DECLINED')['paymentStatus'], 'FAILED'
        )
        self.reject(declined, 'ASSIGN')
        departed = self.through(declined, 'DEPART')
        stopped = self.play(departed, 'LINK_LOST')
        self.assertEqual(stopped['availableSteps'], ['LINK_RESTORED'])
        self.reject(stopped, 'STOP_WAIT')
        restored = self.play(stopped, 'LINK_RESTORED')
        self.assertEqual(restored['availableSteps'], ['RESUME_APPROVED'])
        self.assertEqual(
            self.playback(restored)['checkpoints'][-1]['status'], 'AWAITING_APPROVAL'
        )
        self.reject(restored, 'STOP_WAIT')
        approved = self.play(restored, 'RESUME_APPROVED')
        acknowledged = self.through(approved, 'ROUTE_ACK')
        failed = self.play(acknowledged, 'ROUTE_FAILED')
        self.assertEqual(failed['nextStep'], 'REDEPART')
        self.assertEqual(
            self.evidence(self.finish(failed), 'ALIGHT')['effectiveDestination'], 'S2'
        )

    def start(self, plan: str) -> dict[str, Any]:
        """Start a review on the shared fixture, retrying the same run ID."""
        payload: dict[str, object] = {'plan': plan, 'id': str(uuid4())}
        status, run = self.http.send(ROOT + '/runs', self.admin, payload)
        self.assertEqual(status, 200, run)
        self.assertEqual(
            self.http.send(ROOT + '/runs', self.admin, payload), (200, run)
        )
        return run

    def play(self, run: dict[str, Any], step: str) -> dict[str, Any]:
        """Submit one ordered checkpoint and read committed evidence."""
        status, result = self.http.send(
            f'{ROOT}/runs/{run["id"]}/steps/{step}', self.admin, {}
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

    def reject(self, run: dict[str, Any], step: str) -> None:
        """Assert a case gate blocks the given checkpoint."""
        self.assertEqual(
            self.http.send(f'{ROOT}/runs/{run["id"]}/steps/{step}', self.admin, {}),
            (409, {'code': 'SCENARIO_STEP_OUT_OF_ORDER'}),
        )

    def snapshot(self) -> dict[str, Any]:
        """Read the fleet feed through IF-03 when configured."""
        port = os.environ.get('AMO_DEMO_IF03_PORT')
        status, snapshot = (
            self.http.fms_snapshot(int(port), self.admin)
            if port
            else self.http.send('/api/operations', self.admin)
        )
        self.assertEqual(status, 200, snapshot)
        return snapshot

    def playback(self, run: dict[str, Any]) -> dict[str, Any]:
        """Verify the FMS snapshot is scoped to the run without exposing a fleet vehicle."""
        snapshot = self.snapshot()
        review = cast(dict[str, Any], snapshot['review'])
        self.assertEqual(review['runId'], run['id'])
        self.assertEqual(review['vehicle'], run['vehicleNumber'])
        self.assertTrue(
            all(v['vehicleNo'] != review['vehicle'] for v in snapshot['vehicles'])
        )
        return review

    def assert_not_in_operations(self, run: dict[str, Any]) -> None:
        """Verify the ordinary FMS queue never contains the simulated request."""
        self.assertTrue(
            all(r['id'] != run['requestId'] for r in self.snapshot()['requests'])
        )
