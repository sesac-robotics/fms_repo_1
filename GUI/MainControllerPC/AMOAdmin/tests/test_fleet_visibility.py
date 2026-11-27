"""Exercise offline FMS scenario visibility through the workspace toggle."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.fleet_visibility import visible_fleet
from amo_fms.i18n import Text
from amo_fms.models import Event, Operator, Snapshot, Vehicle
from amo_fms.review_playback import Playback
from amo_fms.workspace import Workspace


def vehicle(number: str) -> Vehicle:
    return Vehicle.parse({'id': number, 'vehicleNo': number, 'status': 'UNKNOWN'})


class FleetVisibilityTest(TestCase):
    def test_normal_view_excludes_scenario_rows_without_mutating_source(self) -> None:
        regular = vehicle('PINKY-01')
        legacy = vehicle('DEMO-REPLAY-01')
        generated = vehicle('DEMO-REVIEW-123')
        events = (
            Event('1', '', 'DEMO_REVIEW_CALL', regular.number, ''),
            Event('2', '', 'ARRIVAL', generated.number, ''),
            Event('3', '', 'ARRIVAL', regular.number, ''),
        )
        source = Snapshot(
            vehicles=(legacy, generated, regular), events=events, demo=True
        )
        normal = visible_fleet(source, False)
        self.assertEqual(normal.vehicles, (regular,))
        self.assertEqual(normal.events, events[2:])
        self.assertIs(visible_fleet(source, True), source)

    def test_toggle_updates_fleet_and_clears_scenario_map_and_details(self) -> None:
        app = QApplication.instance() or QApplication([])
        app.processEvents()
        real = tuple(vehicle(f'PINKY-{n:02d}') for n in range(1, 5))
        synthetic = vehicle('DEMO-REVIEW-123')
        playback = Playback(UUID(int=1), synthetic.number, ())
        source = Snapshot(vehicles=(*real, synthetic), demo=True, review=playback)
        with (
            TemporaryDirectory() as path,
            patch.dict(
                'os.environ',
                {'AMO_FMS_PREVIEW_DIRECTORY': '', 'AMO_FMS_TEST_IMAGES': '1'},
            ),
        ):
            prefs = Preferences(
                QSettings(str(Path(path) / 'fms.ini'), QSettings.Format.IniFormat)
            )
            tr = Text('en')
            workspace = Workspace(
                tr,
                Config('http://127.0.0.1:1', DEFAULT_MAP_ROOT, scenario_review=True),
                prefs,
                Operator('1', 'Operator', '', 'OPERATOR'),
                'monitor',
            )
            monitor = workspace._monitor

            workspace.show_snapshot(source, synthetic.id)
            self.assertFalse(workspace.scenario_demo)
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=4))
            self.assertEqual(monitor._list.count(), 4)
            self.assertIsNone(monitor._map._confirmed._review)
            self.assertEqual(monitor._values['vehicle_no'].text(), real[0].number)

            workspace._review_mode.click()
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=5))
            self.assertEqual(monitor._list.count(), 5)
            self.assertIn(synthetic.number, monitor._list.item(4).text())
            self.assertIs(monitor._map._confirmed._review, playback)
            workspace.show_snapshot(source, real[0].id)
            self.assertEqual(monitor._list.count(), 5)
            monitor._list.setCurrentRow(4)
            self.assertEqual(monitor._values['vehicle_no'].text(), synthetic.number)

            workspace._review_mode.click()
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=4))
            self.assertEqual(monitor._list.count(), 4)
            self.assertIsNone(monitor._map._confirmed._review)
            self.assertEqual(monitor._values['vehicle_no'].text(), real[0].number)
            workspace.close()
