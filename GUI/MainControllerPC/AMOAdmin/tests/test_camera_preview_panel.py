"""Verify the FMS map-area, fleet, and camera selections with synthetic images."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QPushButton

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.i18n import Text
from amo_fms.models import Snapshot
from amo_fms.monitor import FleetMonitor


class CameraPreviewPanelTest(TestCase):
    def test_four_images_share_selection_with_the_map_area_and_fleet(self) -> None:
        app = QApplication.instance() or QApplication([])
        numbers = tuple(f'PINKY-{index:02d}' for index in range(1, 5))
        vehicles = [
            {'id': index, 'vehicleNo': number}
            for index, number in enumerate(numbers, 1)
        ]
        snapshot = Snapshot.parse({'vehicles': vehicles, 'requests': [], 'events': []})
        selections: list[str] = []
        with (
            TemporaryDirectory() as path,
            patch.dict('os.environ', {'AMO_FMS_TEST_IMAGES': '1'}),
        ):
            prefs = Preferences(
                QSettings(str(Path(path) / 'fms.ini'), QSettings.Format.IniFormat)
            )
            monitor = FleetMonitor(
                Text('en'),
                Config('http://127.0.0.1:18085', DEFAULT_MAP_ROOT),
                prefs,
                selections.append,
                lambda: None,
            )
            monitor.show()
            monitor.show_snapshot(snapshot, '1')
            app.processEvents()
            cards = list(monitor._previews._cards.values())
            self.assertEqual(len(cards), 4)
            self.assertTrue(all(not card.icon().isNull() for card in cards))
            self.assertTrue(cards[0].isChecked())
            map_buttons = monitor._map_selection.findChildren(QPushButton)
            map_buttons[2].click()
            self.assertEqual(selections[-1], '3')
            self.assertTrue(cards[2].isChecked())
            self.assertFalse(cards[0].isChecked())
            cards[3].click()
            self.assertEqual(selections[-1], '4')
            self.assertTrue(map_buttons[3].isChecked())
            self.assertEqual(monitor._list.currentRow(), 3)
            monitor._list.setCurrentRow(1)
            self.assertEqual(selections[-1], '2')
            self.assertTrue(cards[1].isChecked())
            monitor._previews._expand.click()
            self.assertEqual(
                [card.isVisible() for card in cards], [False, True, False, False]
            )
            self.assertTrue(monitor._map.isVisible())
            monitor._previews._expand.click()
            self.assertTrue(all(card.isVisible() for card in cards))
            monitor.close()
