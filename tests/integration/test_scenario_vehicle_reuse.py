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
        vehicles = [
            v
            for v in cast(list[dict[str, object]], fresh['vehicles'])
            if str(v['vehicleNo']).startswith('DEMO-REVIEW-')
        ]
        self.assertEqual(len(vehicles), 1)
        self.assertIsNone(vehicles[0]['xM'])
        self.assertFalse(
            any(
                str(e['type']).startswith('DEMO_REVIEW_')
                for e in cast(list[dict[str, object]], fresh['events'])
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
        stage = next(
            e
            for e in cast(list[dict[str, object]], snapshot()['events'])
            if str(e['type']).startswith('DEMO_REVIEW_')
        )
        self.assertEqual(stage['type'], 'DEMO_REVIEW_ASSIGN')
        self.assertEqual(stage['vehicle'], second['vehicleNumber'])
