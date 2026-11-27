"""Verify sharing one synthetic vehicle without sharing review evidence."""

from __future__ import annotations

import os
import unittest
from typing import cast
from uuid import uuid4

from demo_http import DemoHttp

ORIGIN = os.environ.get('AMO_DEMO_HTTP', '')
ROOT = '/api/admin/demo/scenarios/runs'


@unittest.skipUnless(ORIGIN, 'requires isolated demo servers and PostgreSQL')
class ScenarioVehicleReuseTest(unittest.TestCase):
    """Verify the behavior of a new review while an old dispatch is still open."""

    def test_new_run_reuses_vehicle_and_archives_incomplete_review(self) -> None:
        http = DemoHttp(ORIGIN)
        admin = http.login('admin')

        def start(plan: str) -> dict[str, object]:
            payload: dict[str, object] = {'plan': plan, 'id': str(uuid4())}
            status, run = http.send(ROOT, admin, payload)
            self.assertEqual(status, 200, run)
            return run

        def assign(run: dict[str, object]) -> dict[str, object]:
            while (step := run['nextStep']) is not None:
                status, run = http.send(f'{ROOT}/{run["id"]}/steps/{step}', admin, {})
                self.assertEqual(status, 200, (step, run))
                if step == 'ASSIGN':
                    return run
            self.fail('ASSIGN checkpoint unavailable')

        def snapshot() -> dict[str, object]:
            port = os.environ.get('AMO_DEMO_IF03_PORT')
            status, result = (
                http.fms_snapshot(int(port), admin)
                if port
                else http.send('/api/operations', admin)
            )
            self.assertEqual(status, 200, result)
            return result

        first = assign(start('TAXI_APPLIED'))
        second = start('TAXI_APPLY_FAILED')
        self.assertEqual(first['vehicleNumber'], second['vehicleNumber'])
        fresh = snapshot()
        current = cast(dict[str, object], fresh['review'])
        self.assertEqual(current['runId'], second['id'])
        self.assertEqual(current['checkpoints'], [])
        self.assertFalse(
            any(
                str(v['vehicleNo']).startswith('DEMO-REVIEW-')
                for v in cast(list[dict[str, object]], fresh['vehicles'])
            )
        )
        first_path = f'{ROOT}/{first["id"]}'
        self.assertEqual(http.send(first_path, admin), (200, first))
        self.assertEqual(
            http.send(first_path + '/steps/ASSIGN', admin, {}), (200, first)
        )
        self.assertEqual(
            http.send(first_path + '/steps/PICKUP_STOP', admin, {}),
            (409, {'code': 'SCENARIO_RUN_SUPERSEDED'}),
        )
        self.assertNotEqual(assign(second)['requestId'], first['requestId'])
        playback = cast(dict[str, object], snapshot()['review'])
        stages = cast(list[dict[str, object]], playback['checkpoints'])
        self.assertEqual(stages[-1]['step'], 'ASSIGN')
        self.assertEqual(playback['vehicle'], second['vehicleNumber'])

    def test_close_and_clear_scope(self) -> None:
        http = DemoHttp(ORIGIN)
        admin = http.login('admin')
        api = ROOT.removesuffix('/runs')
        before = http.send('/api/operations', admin)[1]
        run_path = f'{ROOT}/{uuid4()}'
        payload: dict[str, object] = {
            'plan': 'TAXI_APPLIED',
            'id': run_path.rsplit('/', 1)[1],
        }
        self.assertEqual(http.send(ROOT, admin, payload)[0], 200)
        self.assertEqual(
            http.send(run_path + '/steps/INITIAL_OCCUPY', admin, {})[0], 200
        )
        status, closed = http.send(run_path + '/reset', admin, {})
        self.assertEqual(status, 200, closed)
        self.assertIsNone(closed['current'])
        self.assertEqual(http.send(run_path, admin)[0], 200)
        self.assertIsNone(http.send('/api/operations', admin)[1]['review'])
        self.assertEqual(
            http.send(run_path + '/steps/INITIAL_CHARGE', admin, {})[0], 409
        )

        status, stale = http.send(api, admin)
        self.assertEqual(status, 200, stale)
        payload['id'] = str(uuid4())
        self.assertEqual(http.send(ROOT, admin, payload)[0], 200)
        counts = cast(dict[str, object], stale['history'])
        self.assertEqual(
            http.send(api + '/history/reset', admin, counts),
            (409, {'code': 'SCENARIO_RESET_CHANGED'}),
        )
        counts = cast(dict[str, object], http.send(api, admin)[1]['history'])
        self.assertEqual(
            http.send(api + '/history/reset', admin, counts),
            (200, {'runs': 0, 'observations': 0, 'current': None}),
        )
        self.assertEqual(http.send(run_path, admin)[0], 404)
        after = http.send('/api/operations', admin)[1]
        for field in ('vehicles', 'requests', 'events'):
            self.assertEqual(before[field], after[field])
