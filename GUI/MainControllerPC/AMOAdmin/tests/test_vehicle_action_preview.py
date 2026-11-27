"""Verify the non-modal FMS preview with synthetic vehicle observations."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.i18n import Text
from amo_fms.models import Operator, Snapshot, Vehicle
from amo_fms.workspace import Workspace


class VehicleActionPreviewTest(TestCase):
    def test_popup_follows_selection_without_leaving_the_map(self) -> None:
        app = QApplication.instance() or QApplication([])
        fleet = tuple(
            Vehicle.parse(
                {'id': i, 'vehicleNo': f'PINKY-{i:02d}', 'connection': 'SIMULATED'}
            )
            for i in range(1, 5)
        )
        scenario = replace(fleet[0], id='5', number='DEMO-REPLAY-01')
        snapshot = Snapshot(vehicles=(*fleet, scenario), demo=True)
        with (
            TemporaryDirectory() as name,
            patch.dict(
                'os.environ',
                {'AMO_FMS_PREVIEW_DIRECTORY': '', 'AMO_FMS_TEST_IMAGES': '1'},
            ),
        ):
            settings = QSettings(
                str(Path(name) / 'fms.ini'), QSettings.Format.IniFormat
            )
            workspace = Workspace(
                Text('en'),
                Config('http://127.0.0.1:1', DEFAULT_MAP_ROOT),
                Preferences(settings),
                Operator('1', 'Operator', '', 'OPERATOR'),
                'monitor',
            )
            workspace.resize(1220, 855)
            workspace.show()
            workspace.show_snapshot(snapshot, fleet[0].id)
            monitor = workspace._monitor
            preview = monitor._action_preview
            cards = tuple(monitor._previews._cards.values())
            self.assertNotIn('commands', workspace._nav)
            self.assertIs(workspace._stack.currentWidget(), monitor)

            monitor._actions.click()
            app.processEvents()
            self.assertTrue(preview.isVisible())
            self.assertTrue(monitor._map.isVisible())
            self.assertTrue(all(card.isVisible() for card in cards))
            self.assertIn(fleet[0].number, preview._title.text())
            preview._inspect.click()
            self.assertIn(fleet[0].number, preview._message.text())

            cards[1].click()
            self.assertTrue(preview.isVisible())
            self.assertIn(fleet[1].number, preview._title.text())
            self.assertEqual(preview._message.text(), '')
            self.assertFalse(preview._confirm.isVisible())
            preview._inspect.click()
            preview._confirm.click()
            self.assertIn(fleet[1].number, preview._message.text())
            self.assertNotIn(fleet[0].number, preview._message.text())

            revised = replace(fleet[1], connection='UNKNOWN')
            workspace.show_snapshot(
                replace(snapshot, vehicles=(fleet[0], revised, *fleet[2:], scenario)),
                revised.id,
            )
            self.assertTrue(preview.isVisible())
            self.assertFalse(preview._inspect.isEnabled())
            self.assertEqual(preview._message.text(), '')

            QTest.keyClick(preview, Qt.Key.Key_Escape)
            self.assertFalse(preview.isVisible())
            self.assertEqual(monitor._values['vehicle_no'].text(), revised.number)

            cards[0].click()
            monitor._actions.click()
            workspace._review_mode.click()
            monitor._scenario_card.click()
            self.assertFalse(preview.isVisible())
            self.assertFalse(monitor._actions.isEnabled())
            self.assertTrue(monitor._map.isVisible())
            self.assertTrue(all(card.isVisible() for card in cards))
            workspace.close()
