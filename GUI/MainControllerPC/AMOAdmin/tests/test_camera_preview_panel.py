"""Verify the FMS map-area and camera selections with synthetic images."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PyQt6.QtCore import QBuffer, QIODevice, QSettings, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
)

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.i18n import Text
from amo_fms.models import Snapshot
from amo_fms.monitor import FleetMonitor
from amo_fms.theme import palette, stylesheet


class CameraPreviewPanelTest(TestCase):
    def test_four_images_share_selection_with_the_map_area(self) -> None:
        app = QApplication.instance() or QApplication([])
        numbers = tuple(f'PINKY-{index:02d}' for index in range(1, 5))
        vehicles = [
            {'id': index, 'vehicleNo': number, 'status': 'IDLE'}
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
            monitor.setStyleSheet(stylesheet(palette(prefs.theme)))
            monitor.resize(1440, 850)
            monitor.show()
            monitor.show_snapshot(snapshot, '1')
            app.processEvents()
            cards = list(monitor._previews._cards.values())
            self.assertEqual(len(cards), 4)
            self.assertTrue(
                all(not card.surface.frame_rect().isEmpty() for card in cards)
            )
            self.assertTrue(cards[0].isChecked())
            self.assertTrue(all(card.surface.height() >= 48 for card in cards))
            self.assertFalse(monitor.findChildren(QScrollArea))
            split = monitor.findChild(QSplitter)
            previous_width = cards[0].surface.width()
            split.setSizes([480, 960])
            app.processEvents()
            self.assertTrue(
                all(card.surface.width() > previous_width for card in cards)
            )
            self.assertTrue(monitor._map.isVisible())
            for card in cards:
                self.assertTrue(card.rect().contains(card.surface.geometry()))
                self.assertTrue(card.rect().contains(card._caption.geometry()))
                self.assertLess(
                    card.surface.geometry().bottom(), card._caption.geometry().top()
                )
            map_buttons = monitor._map_selection.findChildren(QPushButton)
            map_buttons[2].click()
            self.assertEqual(selections[-1], '3')
            self.assertTrue(cards[2].isChecked())
            self.assertFalse(cards[0].isChecked())
            cards[3].click()
            self.assertEqual(selections[-1], '4')
            self.assertTrue(map_buttons[3].isChecked())
            self.assertEqual(monitor._values['vehicle_no'].text(), 'PINKY-04')
            self.assertIn(Text('en').status('IDLE'), cards[3]._caption.text())
            self.assertFalse(monitor.findChildren(QListWidget))
            QTest.mouseDClick(cards[1], Qt.MouseButton.LeftButton)
            self.assertEqual(selections[-1], '2')
            self.assertTrue(cards[1].isChecked())
            viewer = monitor._previews._viewer
            self.assertTrue(viewer.isVisible())
            self.assertTrue(all(card.isVisible() for card in cards))
            self.assertTrue(monitor._map.isVisible())
            app.processEvents()
            enlarged = monitor._previews._viewer_surface
            self.assertGreater(
                enlarged.frame_rect().height(), cards[1].surface.frame_rect().height()
            )
            QTest.keyClick(viewer, Qt.Key.Key_Escape)
            self.assertFalse(viewer.isVisible())
            self.assertTrue(all(card.isVisible() for card in cards))
            monitor.close()

    def test_face_status_tracks_the_preview_that_is_actually_rendered(self) -> None:
        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as name:
            directory = Path(name)
            preview = directory / 'PINKY-01.preview'
            image = QImage(640, 480, QImage.Format.Format_RGB32)
            image.fill(0xFF406080)
            output = QBuffer()
            output.open(QIODevice.OpenModeFlag.WriteOnly)
            self.assertTrue(image.save(output, 'JPEG'))
            jpeg = bytes(output.data())
            rows = [{'id': 1, 'vehicleNo': 'PINKY-01'}]
            snapshot = Snapshot.parse({'vehicles': rows, 'requests': [], 'events': []})
            with patch.dict(
                'os.environ',
                {
                    'AMO_FMS_TEST_IMAGES': '0',
                    'AMO_FMS_PREVIEW_DIRECTORY': name,
                },
            ):
                prefs = Preferences(
                    QSettings(str(directory / 'test.ini'), QSettings.Format.IniFormat)
                )
                monitor = FleetMonitor(
                    Text('en'),
                    Config('http://127.0.0.1:18085', DEFAULT_MAP_ROOT),
                    prefs,
                    lambda _: None,
                    lambda: None,
                )
                monitor.show()
                app.processEvents()
                card = monitor._previews._cards['PINKY-01']
                for count, expected in [
                    (0, 'No faces detected'),
                    (2, 'Faces masked · 2 regions'),
                ]:
                    preview.write_bytes(b'AMOV2' + bytes([count]) + jpeg)
                    preview.chmod(0o600)
                    monitor.show_snapshot(snapshot, '1')
                    self.assertIn(expected, card.accessibleName())
                    self.assertFalse(card.surface.frame_rect().isEmpty())
                preview.unlink()
                monitor.show_snapshot(snapshot, '1')
                self.assertIn('Waiting for video', card.accessibleName())
                self.assertTrue(card.surface.frame_rect().isEmpty())
                QTest.mouseDClick(card, Qt.MouseButton.LeftButton)
                self.assertFalse(monitor._previews._viewer.isVisible())
                monitor.close()
