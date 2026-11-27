"""Regression tests for the local FMS preview boundaries."""

from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from PyQt6.QtCore import QPointF, QRectF

from amo_fms.config import preview_endpoint
from amo_fms.desktop_loopback import CALLBACK_PATH, callback_code
from amo_fms.desktop_sign_in import code_challenge, sign_in_url
from amo_fms.i18n import Text
from amo_fms.map_preview import _badge_bounds, _label_areas, map_fraction
from amo_fms.models import Operator, RideRequest, Snapshot


class PreviewContractTests(unittest.TestCase):
    """Keep operational evidence separate from requests and previews."""

    def test_only_confirmed_revision_changes_route_projection(self) -> None:
        request = {'id': 12, 'pickup': 'S1', 'destination': 'S2', 'status': 'ON_TRIP'}
        pending = RideRequest.parse({**request, 'effectiveDestination': 'S4'})
        self.assertIsNone(pending.applied)
        applied = RideRequest.parse(
            {**request, 'effectiveDestination': 'S4', 'appliedRevisionId': 7}
        )
        self.assertEqual(applied.destination, 'S2')
        self.assertIsNotNone(applied.applied)
        assert applied.applied is not None
        self.assertEqual(
            (applied.applied.revision, applied.applied.destination), (7, 'S4')
        )

    def test_nullable_vehicle_in_a_waiting_event(self) -> None:
        snapshot = Snapshot.parse(
            {
                'demo': True,
                'vehicles': [],
                'requests': [],
                'events': [
                    {
                        'id': 14,
                        'time': '2026-11-22T00:00:00Z',
                        'type': 'WAITING',
                        'vehicle': None,
                        'detail': 'Request not assigned',
                    }
                ],
            }
        )
        self.assertTrue(snapshot.demo)
        self.assertEqual(snapshot.events[0].vehicle, '')
        self.assertEqual(snapshot.events[0].type, 'WAITING')

    def test_simulated_link_does_not_imply_dispatch_eligibility(self) -> None:
        snapshot = Snapshot.parse(
            {
                'demo': True,
                'vehicles': [
                    {
                        'id': 1,
                        'vehicleNo': 'PINKY-01',
                        'status': 'AVAILABLE',
                        'batteryPercent': 82,
                        'connection': 'SIMULATED',
                        'xM': 1.22,
                        'yM': 0,
                        'dispatchEnabled': False,
                    }
                ],
                'requests': [],
                'events': [],
            }
        )
        vehicle = snapshot.vehicles[0]
        self.assertFalse(vehicle.connected)
        self.assertTrue(vehicle.can_preview)
        self.assertIs(vehicle.dispatch_enabled, False)
        self.assertEqual(map_fraction(vehicle.position_m), (0.5, 1.0))
        self.assertIsNone(map_fraction((0, 2.226)))

    def test_passenger_cannot_open_fms(self) -> None:
        with self.assertRaises(PermissionError):
            Operator.parse({'id': 1, 'role': 'PASSENGER'})

    def test_four_vehicles_keep_their_individual_measurements(self) -> None:
        rows = [
            {
                'id': number,
                'vehicleNo': f'PINKY-{number:02d}',
                'status': 'AVAILABLE',
                'connection': 'SIMULATED',
                'dispatchEnabled': False,
                'xM': 0.3 * number,
                'yM': 0.4,
                'yawRad': 0.5 * number,
                'speedMps': 0,
            }
            for number in range(1, 5)
        ]
        snapshot = Snapshot.parse({'vehicles': rows, 'requests': [], 'events': []})
        self.assertEqual([v.id for v in snapshot.vehicles], ['1', '2', '3', '4'])
        self.assertEqual([v.yaw_rad for v in snapshot.vehicles], [0.5, 1.0, 1.5, 2.0])
        self.assertTrue(all(v.speed_mps == 0 for v in snapshot.vehicles))
        self.assertTrue(all(v.dispatch_enabled is False for v in snapshot.vehicles))
        self.assertEqual(len({v.position_m for v in snapshot.vehicles}), 4)

    def test_vehicle_badge_avoids_stop_labels(self) -> None:
        board = QRectF(60, 115, 380, 348)
        labels = _label_areas(board)
        anchor = labels[1].center() + QPointF(0, 17)
        badge = _badge_bounds(anchor, 13, board, list(labels))
        self.assertIsNotNone(badge)
        self.assertTrue(board.contains(badge))
        self.assertFalse(any(badge.intersects(label) for label in labels))

    def test_known_event_detail_is_localized_without_rewriting_unknown_text(
        self,
    ) -> None:
        for language in ('ko', 'zh-Hans'):
            with self.subTest(language=language):
                text = Text(language)
                self.assertEqual(
                    text.status('REQUEST_RECEIVED'), text('status_received')
                )
                self.assertNotEqual(
                    text.event_detail('Passenger request received'),
                    'Passenger request received',
                )
                self.assertEqual(
                    text.event_detail('Future evidence'), 'Future evidence'
                )


class OAuthBoundaryTests(unittest.TestCase):
    """Guard the browser handoff and exact callback correlation."""

    def test_rfc7636_s256_example(self) -> None:
        self.assertEqual(
            code_challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'),
            'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
        )

    def test_loopback_rejects_wrong_or_ambiguous_state(self) -> None:
        code = 'a' * 43
        for query in (
            f'state=no&code={code}',
            f'state=ok&state=&code={code}',
            f'state=ok&state=no&code={code}',
            f'state=%C3%A9&code={code}',
            f'state=ok&code={code}&code=',
            f'state=ok&error=access_denied&code={code}',
            'state=ok&code=short',
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                callback_code(f'{CALLBACK_PATH}?{query}', 'ok')
        with self.assertRaises(ValueError):
            callback_code(f'/?state=ok&code={code}', 'ok')
        self.assertEqual(
            callback_code(f'{CALLBACK_PATH}?state=ok&code={code}', 'ok'), code
        )
        self.assertEqual(
            callback_code(f'{CALLBACK_PATH}?state=ok&error=access_denied', 'ok'), ''
        )

    def test_bridge_query_excludes_private_verifier(self) -> None:
        verifier = 'A' * 64
        url = sign_in_url('http://127.0.0.1:5175', 33217, verifier, 'test-state')
        parts = urlsplit(url)
        self.assertEqual(parts.path, '/desktop-sign-in')
        self.assertEqual(
            parse_qs(parts.query),
            {
                'port': ['33217'],
                'challenge': [code_challenge(verifier)],
                'state': ['test-state'],
            },
        )
        self.assertNotIn(verifier, url)

    def test_browser_accepts_only_https_or_loopback_http_origin(self) -> None:
        self.assertEqual(
            preview_endpoint('http://127.0.0.1:5175/'), 'http://127.0.0.1:5175'
        )
        self.assertEqual(
            preview_endpoint('https://admin.example'), 'https://admin.example'
        )
        for origin in (
            'http://admin.example',
            'https://user@admin.example',
            'https://admin.example/path',
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                preview_endpoint(origin)
