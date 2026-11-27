"""Verify the per-intersection timing editor behind each signals-page card."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication  # noqa: E402
from test_signal_page import FakeSender, row, snapshot, visible_texts  # noqa: E402

from amo_fms.i18n import Text  # noqa: E402
from amo_fms.signal_page import SignalsPage  # noqa: E402


class JunctionDetailTest(unittest.TestCase):
    """Linked fields move together; apply sends only what changed."""

    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_details_apply_only_changed_plans_then_return(self) -> None:
        sender = FakeSender()
        page = SignalsPage(Text('en'), lambda: None, sender)  # type: ignore[arg-type]
        page.show_snapshot(snapshot(row(), row(signalId='SIG-02')), '')
        page.cards['signal_junction_plus'].detail.click()
        self.assertIs(page.stack.currentWidget(), page.detail)
        texts = visible_texts(page)
        self.assertIn('Centre crossroads signal timing', texts)
        self.assertIn('Northbound green', texts)
        self.assertIn('Southbound green', texts)
        self.assertIn('Westbound yellow', texts)
        first, second = (editor for editor, _ids in page.detail._editors)
        second._boxes[0].setValue(12.0)  # southbound green moves northbound too
        self.assertEqual(first.values()[0], 12.0)
        first._boxes[0].setValue(10.0)
        first._boxes[3].setValue(2.5)  # all red is shared
        self.assertEqual(second.values()[3], 2.5)
        first._boxes[1].setValue(14.0)  # eastbound green is its own
        second._boxes[4].setValue(4.0)  # westbound yellow is its own
        self.assertEqual(first.values(), (10.0, 14.0, 3.0, 2.5, 3.0))
        self.assertEqual(second.values(), (10.0, 10.0, 3.0, 2.5, 4.0))
        page.detail.apply.click()
        self.assertEqual(
            sender.sent,
            [
                ('SIG-01', 'PLAN 10000 14000 3000 2500 3000 14000'),
                ('SIG-02', 'PLAN 10000 10000 3000 2500 4000 17000'),
            ],
        )
        self.assertEqual(page.stack.currentIndex(), 0)
        card = page.cards['signal_junction_plus']
        self.assertEqual(card.status.text(), Text('en')('signal_sending'))

    def test_crossing_ends_share_every_field(self) -> None:
        sender = FakeSender()
        page = SignalsPage(Text('en'), lambda: None, sender)  # type: ignore[arg-type]
        page.show_snapshot(snapshot(row(signalId='SIG-03'), row(signalId='SIG-04')), '')
        page.cards['signal_junction_t'].detail.click()
        texts = visible_texts(page)
        self.assertIn('Eastbound green', texts)
        self.assertIn('Westbound yellow', texts)
        east, west = (editor for editor, _ids in page.detail._editors)
        west._boxes[1].setValue(14.0)  # car green
        west._boxes[4].setValue(4.0)  # car yellow
        east._boxes[0].setValue(12.0)  # pedestrian green
        self.assertEqual(east.values(), west.values())
        page.detail.apply.click()
        plan = 'PLAN 12000 14000 3000 2000 4000 0'
        self.assertEqual(sender.sent, [('SIG-03', plan), ('SIG-04', plan)])

    def test_single_board_details_and_plan_mismatch_warning(self) -> None:
        sender = FakeSender()
        page = SignalsPage(Text('en'), lambda: None, sender)  # type: ignore[arg-type]
        other = row(
            signalId='SIG-02', plan={**row()['state']['plan'], 'yellowMs': 4000}
        )  # type: ignore[index]
        page.show_snapshot(snapshot(row(), other, row(signalId='SIG-03')), '')
        self.assertTrue(page.cards['signal_junction_plus'].mismatch.isVisibleTo(page))
        self.assertFalse(page.cards['signal_junction_t'].mismatch.isVisibleTo(page))
        page.cards['signal_junction_t'].detail.click()
        self.assertIn('Pedestrians green', visible_texts(page))
        page.detail.apply.click()  # nothing changed: nothing is sent
        self.assertEqual(sender.sent, [])
        self.assertEqual(page.stack.currentIndex(), 0)


if __name__ == '__main__':
    unittest.main()
