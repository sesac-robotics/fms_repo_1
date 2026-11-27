"""Verify SignalKit rows decode safely and render on the FMS signals page."""

from __future__ import annotations

import os
import unittest
from collections.abc import Callable

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication, QLabel  # noqa: E402

from amo_fms.i18n import Text, catalog  # noqa: E402
from amo_fms.models import Snapshot  # noqa: E402
from amo_fms.signal_page import SignalsPage  # noqa: E402


def row(**state: object) -> dict[str, object]:
    """Return one signal row in the /api/operations shape."""
    base: dict[str, object] = {
        'signalId': 'SIG-01',
        'seq': 42,
        'phase': 'NORTH_GREEN',
        'mode': 'AUTO',
        'holdTarget': None,
        'remainingMs': 7300,
        'uptimeMs': 123456,
        'plan': {
            'northGreenMs': 10000,
            'eastGreenMs': 10000,
            'yellowMs': 3000,
            'allRedMs': 2000,
        },
        'planPending': False,
        'lastCommand': '',
        'commandResult': 'NONE',
    }
    base.update(state)
    return {'state': base, 'receivedAt': '2026-11-26T05:56:10.437365Z'}


def snapshot(*signals: object) -> Snapshot:
    """Parse a minimal valid operations snapshot carrying the given signal rows."""
    return Snapshot.parse(
        {'vehicles': [], 'requests': [], 'events': [], 'signals': list(signals)}
    )


class SignalReadingsTest(unittest.TestCase):
    """Exercise the server shape and lamp mapping."""

    def test_missing_signals_field_keeps_legacy_snapshot_readable(self) -> None:
        snapshot = Snapshot.parse({'vehicles': [], 'requests': [], 'events': []})
        self.assertEqual(snapshot.signals, ())

    def test_snapshot_keeps_signal_and_pinky_battery_rows(self) -> None:
        operations = Snapshot.parse(
            {
                'vehicles': [],
                'requests': [],
                'events': [],
                'signals': [row()],
                'pinkyBatteries': [
                    {'deviceId': 'PP_00001', 'percent': 70, 'voltage': 8}
                ],
            }
        )
        self.assertEqual(operations.signals[0].signal_id, 'SIG-01')
        self.assertEqual(operations.pinky_batteries[0].percent, 70)

    def test_reads_a_signal_and_maps_lamps(self) -> None:
        (reading,) = snapshot(row()).signals
        self.assertEqual(reading.signal_id, 'SIG-01')
        self.assertEqual(reading.lamps(), ('G', 'R'))
        self.assertEqual(reading.plan_text(), '10s / 10s / 3s / 2s')
        hold = row(phase='EAST_YELLOW', mode='HOLD', holdTarget='NORTH_GREEN')
        (held,) = snapshot(hold).signals
        self.assertEqual(held.lamps(), ('R', 'Y'))
        self.assertEqual(held.hold_target, 'NORTH_GREEN')

    def test_skips_malformed_rows_and_keeps_valid_ones(self) -> None:
        bad = [
            None,
            {'state': None},
            row(phase='BLUE'),
            row(mode='MANUAL'),
            row(holdTarget='NORTH_YELLOW'),
            row(remainingMs=-1),
            row(remainingMs=True),
            row(plan={'northGreenMs': 1}),
            row(planPending='no'),
        ]
        signals = snapshot(*bad, row(signalId='SIG-02')).signals
        self.assertEqual([s.signal_id for s in signals], ['SIG-02'])

    def test_every_locale_has_the_signal_keys(self) -> None:
        keys = {k for k in catalog('en') if k.startswith(('signal', 'phase_'))}
        self.assertGreaterEqual(len(keys), 20)
        for language in ('ko', 'zh-Hans'):
            self.assertLessEqual(keys, set(catalog(language)), language)


def visible_texts(page: SignalsPage) -> set[str]:
    """Return the text of every label the page currently shows."""
    return {w.text() for w in page.findChildren(QLabel) if w.isVisibleTo(page)}


class FakeSender:
    """Records commands instead of calling the gateway."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, signal_id: str, command: str, done: Callable[[str], None]) -> None:
        self.sent.append((signal_id, command))
        done('signal_queued')


class SignalsPageTest(unittest.TestCase):
    """Render the page offscreen and read back the labels."""

    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_groups_boards_by_intersection(self) -> None:
        page = SignalsPage(Text('en'), lambda: None)
        page.show_snapshot(snapshot(), '')
        self.assertIn(Text('en')('signal_none'), visible_texts(page))
        held = row(mode='HOLD', holdTarget='NORTH_GREEN', remainingMs=0)
        boards = (held, row(signalId='SIG-02'), row(signalId='SIG-03'))
        page.show_snapshot(snapshot(*boards), '')
        self.app.processEvents()
        texts = visible_texts(page)
        self.assertNotIn(Text('en')('signal_none'), texts)
        self.assertIn('North T-junction', texts)
        self.assertIn('Centre crossroads', texts)
        self.assertNotIn('Other signals', texts)
        self.assertEqual(
            set(page.cards['signal_junction_plus'].blocks), {'SIG-01', 'SIG-02'}
        )
        self.assertEqual(set(page.cards['signal_junction_t'].blocks), {'SIG-03'})
        self.assertIn('a · Northbound', texts)
        self.assertIn('b · Westbound', texts)
        self.assertIn('a · Pedestrians', texts)
        self.assertIn('Holding', texts)
        self.assertIn('Next change in 7.3 s', texts)
        self.assertIn('● Receiving from the server', texts)


if __name__ == '__main__':
    unittest.main()
