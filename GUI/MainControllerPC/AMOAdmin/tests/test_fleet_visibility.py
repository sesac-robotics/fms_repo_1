"""Exercise offline FMS scenario visibility through the workspace toggle."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QScrollArea

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.fleet_visibility import visible_fleet
from amo_fms.i18n import Text
from amo_fms.models import Event, Operator, Snapshot, Vehicle
from amo_fms.pinky_batteries import PinkyBattery
from amo_fms.review_playback import Checkpoint, Playback
from amo_fms.theme import palette, stylesheet
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

    def test_normal_view_preserves_reported_charge_and_filters_demo_batteries(
        self,
    ) -> None:
        physical = replace(
            vehicle('PINKY-01'),
            battery_percent=61,
            status='CHARGING',
            connection='CONNECTED',
            sample=('camera-unit-test', 1, '2026-11-27T00:00:00Z'),
        )
        simulated = replace(
            vehicle('PINKY-02'),
            battery_percent=64,
            status='STOPPED',
            connection='DISCONNECTED',
            sample=('demo-1', 1, '2026-11-22T00:00:00Z'),
        )
        real_battery = PinkyBattery('fixture-real', 61, 8, False)
        demo_battery = PinkyBattery('fixture-demo', 64, 8, True)
        snapshot = Snapshot(
            vehicles=(physical, simulated),
            demo=True,
            pinky_batteries=(real_battery, demo_battery),
        )
        normal = visible_fleet(snapshot, False)
        self.assertIs(normal.vehicles[0], physical)
        self.assertEqual(normal.vehicles[1].status, 'UNKNOWN')
        self.assertIsNone(normal.vehicles[1].battery_percent)
        self.assertEqual(normal.pinky_batteries, (real_battery,))
        self.assertIs(visible_fleet(snapshot, True), snapshot)

    def test_toggle_updates_fleet_and_clears_scenario_map_and_details(self) -> None:
        app = QApplication.instance() or QApplication([])
        app.processEvents()
        base = tuple(vehicle(f'PINKY-{n:02d}') for n in range(1, 5))
        charging = replace(
            base[2], battery_percent=56, status='CHARGING', connection='SIMULATED'
        )
        real = (*base[:2], charging, base[3])
        legacy = vehicle('DEMO-REPLAY-01')
        playback = Playback(
            UUID(int=1), 'DEMO-REVIEW-123', (Checkpoint('STOP_WAIT', 'STOPPED', ''),)
        )
        source = Snapshot(vehicles=(*real, legacy), demo=True, review=playback)
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
            workspace.setStyleSheet(stylesheet(palette(prefs.theme)))
            workspace.resize(1220, 855)
            workspace.show()
            monitor = workspace._monitor

            workspace.show_snapshot(source, real[0].id)
            self.assertFalse(workspace.scenario_demo)
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=4))
            self.assertFalse(monitor._scenario_card.isVisible())
            self.assertIsNone(monitor._map._confirmed._review)
            self.assertEqual(monitor._values['vehicle_no'].text(), real[0].number)

            charge_card = monitor._previews._cards[charging.number]
            charge_card.click()
            self.assertIn(tr('not_received'), charge_card._caption.text())
            self.assertEqual(monitor._values['battery'].text(), tr('not_received'))
            self.assertEqual(monitor._values['status'].text(), tr('not_received'))

            workspace._review_mode.click()
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=5))
            self.assertIn(tr.status('CHARGING'), charge_card._caption.text())
            self.assertEqual(monitor._values['battery'].text(), '56%')
            self.assertTrue(monitor._scenario_card.isVisible())
            self.assertIn('No camera', monitor._scenario_card.text())
            self.assertIn(playback.vehicle, monitor._scenario_card.text())
            self.assertNotIn(legacy.number, monitor._scenario_card.text())
            self.assertIs(monitor._map._confirmed._review, playback)
            self.assertFalse(monitor._map._confirmed._selected)
            monitor._scenario_card.click()
            self.assertTrue(monitor._map._confirmed._selected)
            self.assertEqual(monitor._values['vehicle_no'].text(), playback.vehicle)
            self.assertEqual(monitor._values['status'].text(), tr.status('STOPPED'))
            self.assertTrue(monitor._detail_stage.isVisible())
            app.processEvents()
            self.assertFalse(monitor.findChildren(QScrollArea))
            self.assertTrue(monitor._map.isVisible())
            for card in monitor._previews._cards.values():
                self.assertTrue(card.isVisible())
                self.assertGreaterEqual(card.surface.height(), 48)
                self.assertTrue(
                    monitor.rect().contains(
                        card.mapTo(monitor, card.rect().bottomRight())
                    )
                )
            self.assertGreater(
                monitor._values['position'].x(), monitor._values['status'].x()
            )
            self.assertFalse(monitor._actions.isEnabled())

            workspace._review_mode.click()
            self.assertEqual(monitor._count.text(), tr('fleet_count', count=4))
            self.assertFalse(monitor._scenario_card.isVisible())
            self.assertIsNone(monitor._map._confirmed._review)
            self.assertFalse(monitor._detail_stage.isVisible())
            self.assertIn(tr('not_received'), charge_card._caption.text())
            self.assertEqual(monitor._values['vehicle_no'].text(), real[0].number)

            workspace.show_snapshot(Snapshot(vehicles=(*real, legacy)), real[0].id)
            workspace._review_mode.click()
            self.assertIn(legacy.number, monitor._scenario_card.text())
            monitor._scenario_card.click()
            self.assertEqual(monitor._values['vehicle_no'].text(), legacy.number)
            workspace.close()
