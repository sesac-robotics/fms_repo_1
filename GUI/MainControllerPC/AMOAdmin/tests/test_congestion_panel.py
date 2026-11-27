"""Verify that the optional offline forecast is rendered through normal FMS navigation."""

import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.congestion_panel import CongestionPanel
from amo_fms.congestion_trace import Trace
from amo_fms.i18n import Text
from amo_fms.models import Operator, Snapshot
from amo_fms.workspace import Workspace


class CongestionPanelTest(unittest.TestCase):
    """Validate map identity, time cursor, and coexistence with live pages."""

    def test_visible_navigation_values_and_invalid_map(self) -> None:
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'forecast.json'
            map_path = DEFAULT_MAP_ROOT / 'amo-map-confirmed.png'
            payload = {
                'version': 1,
                'kind': 'synthetic-intersection-replay',
                'run_id': str(uuid4()),
                'intersection_id': 'central-crossing',
                'image_anchor': [0.45, 0.46],
                'vehicle_count': 4,
                'ticks_per_second': 10,
                'map_sha256': sha256(map_path.read_bytes()).hexdigest(),
                'forecasts': [
                    {
                        'tick': tick,
                        'horizon_s': horizon,
                        'model': {'queue': 2, 'wait_s': tick / 10},
                        'baseline': {'queue': 1, 'wait_s': 2.5},
                        'observed': {'queue': 3, 'wait_s': 1},
                    }
                    for tick in (0, 20)
                    for horizon in (10, 30)
                ],
            }
            source.write_text(json.dumps(payload))
            prefs = Preferences(
                QSettings(str(root / 'test.ini'), QSettings.Format.IniFormat)
            )
            config = Config(
                'http://127.0.0.1:18085', DEFAULT_MAP_ROOT, congestion_trace=source
            )
            operator = Operator('1', 'Demo', 'staff@amo.test', 'ADMIN')
            workspace = Workspace(Text('en'), config, prefs, operator, 'monitor')
            try:
                workspace.show()
                workspace.navigate('forecast_title')
                workspace.show_snapshot(Snapshot(), '')
                app.processEvents()
                panel = workspace.findChild(CongestionPanel)
                assert panel is not None
                self.assertTrue(panel.isVisible())
                self.assertEqual(panel._table.rowCount(), 2)
                panel._slider.setValue(1)
                model = panel._table.item(1, 1)
                assert model is not None
                self.assertEqual(model.text(), '2.0 vehicles · 2.0 s')
                self.assertIn('2.0 s', panel._time.text())
                payload['map_sha256'] = '0' * 64
                source.write_text(json.dumps(payload))
                with self.assertRaisesRegex(ValueError, 'map does not match'):
                    Trace.read(source, map_path)
            finally:
                workspace.close()
