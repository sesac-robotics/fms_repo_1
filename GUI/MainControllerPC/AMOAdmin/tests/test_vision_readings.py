"""Verify optional Vision rows do not affect the existing fleet snapshot."""

from __future__ import annotations

import unittest

from amo_fms.i18n import Text
from amo_fms.models import Snapshot
from amo_fms.vision_readings import vehicle_vision_summary


class VisionReadingsTest(unittest.TestCase):
    """Exercise the server's shape and the selected-vehicle display."""

    def test_missing_vision_field_keeps_legacy_snapshot_readable(self) -> None:
        snapshot = Snapshot.parse({'vehicles': [], 'requests': [], 'events': []})
        self.assertEqual(snapshot.vision, ())
        self.assertEqual(
            vehicle_vision_summary(snapshot.vision, 'PINKY-01', Text('en')),
            'No observation',
        )

    def test_displays_only_the_selected_vehicle_and_preserves_the_frame(self) -> None:
        observation = {
            'vehicleNo': 'PINKY-01',
            'source': 'TRAFFIC_RULES',
            'frameId': 'camera-1:391',
            'capturedAt': '2026-11-26T01:00:00.100Z',
            'outcome': 'DETECTED',
            'label': 'EXAMPLE_SIGNAL',
        }
        snapshot = Snapshot.parse(
            {
                'vehicles': [],
                'requests': [],
                'events': [],
                'vision': [
                    None,
                    {'observation': observation, 'receivedAt': '2026-11-26T01:00:01Z'},
                ],
            }
        )
        self.assertEqual(len(snapshot.vision), 1)
        self.assertIn(
            'Detected (EXAMPLE_SIGNAL)',
            vehicle_vision_summary(snapshot.vision, 'PINKY-01', Text('en')),
        )
        self.assertEqual(
            vehicle_vision_summary(snapshot.vision, 'PINKY-02', Text('en')),
            'No observation',
        )
        self.assertIn('camera-1:391', snapshot.vision[0].admin_summary(Text('en')))
