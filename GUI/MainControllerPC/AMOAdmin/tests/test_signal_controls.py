"""Verify the map signals, the plan editor and the command sender."""

from __future__ import annotations

import os
import unittest
from typing import Any

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QObject, QPointF, pyqtSignal  # noqa: E402
from PyQt6.QtNetwork import QNetworkRequest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from amo_fms.config import DEFAULT_MAP_ROOT  # noqa: E402
from amo_fms.i18n import Text  # noqa: E402
from amo_fms.signal_commands import SignalCommandSender, result_key  # noqa: E402
from amo_fms.signal_layout import INTERSECTIONS  # noqa: E402
from amo_fms.signal_map import SignalMap  # noqa: E402
from amo_fms.signal_plan_editor import (  # noqa: E402
    PlanEditor,
    junction_agrees,
    plan_command,
)

APP = QApplication.instance() or QApplication([])


class PlanCommandTest(unittest.TestCase):
    """The editor builds only commands the firmware and server accept."""

    def test_builds_millisecond_plans_inside_the_ranges(self) -> None:
        self.assertEqual(
            plan_command((15.0, 8.0, 3.0, 2.0, 4.0)), 'PLAN 15000 8000 3000 2000 4000 0'
        )
        self.assertEqual(
            plan_command((3.0, 120.0, 10.0, 1.0, 2.0), 17000),
            'PLAN 3000 120000 10000 1000 2000 17000',
        )
        self.assertEqual(
            plan_command((7.5, 7.5, 2.5, 1.5, 2.5)), 'PLAN 7500 7500 2500 1500 2500 0'
        )

    def test_refuses_unsafe_or_incomplete_plans(self) -> None:
        self.assertIsNone(plan_command((2.9, 8.0, 3.0, 2.0, 3.0)))
        self.assertIsNone(plan_command((15.0, 121.0, 3.0, 2.0, 3.0)))
        self.assertIsNone(plan_command((15.0, 8.0, 1.9, 2.0, 3.0)))
        self.assertIsNone(plan_command((15.0, 8.0, 3.0, 0.5, 3.0)))
        self.assertIsNone(plan_command((15.0, 8.0, 3.0, 2.0, 10.5)))
        self.assertIsNone(plan_command((15.0, 8.0, 3.0, 2.0)))
        self.assertIsNone(plan_command((15.0, 8.0, 3.0, 2.0, 3.0), 130001))

    def test_junction_plans_must_fit_one_cycle(self) -> None:
        east = (10000, 12000, 3000, 2000, 4000, 10000)
        west = (10000, 8000, 3000, 2000, 2000, 16000)
        self.assertTrue(junction_agrees([east, west]))
        self.assertFalse(junction_agrees([east, (*west[:5], 0)]))  # partner unknown
        self.assertFalse(junction_agrees([east, (11000, *west[1:])]))  # shared field

    def test_maps_gateway_statuses_to_messages(self) -> None:
        self.assertEqual(result_key(202), 'signal_queued')
        self.assertEqual(result_key(400), 'signal_rejected_command')
        self.assertEqual(result_key(403), 'signal_denied')
        self.assertEqual(result_key(404), 'signal_unknown')
        self.assertEqual(result_key(502), 'signal_send_failed')


class PlanEditorTest(unittest.TestCase):
    """Reported plans fill the fields until the operator edits them."""

    def test_keeps_unsaved_edits_and_builds_the_command(self) -> None:
        editor = PlanEditor(Text('en'), 'SIG-01', {'a': 'N', 'b': 'E'})
        editor.show_plan((10000, 10000, 3000, 2000, 3000, 0))
        self.assertEqual(editor.values(), (10.0, 10.0, 3.0, 2.0, 3.0))
        self.assertFalse(editor.changed())
        editor._boxes[0].setValue(15.0)
        editor.show_plan((10000, 10000, 3000, 2000, 3000, 0))
        self.assertEqual(editor.values()[0], 15.0)
        self.assertTrue(editor.changed())
        self.assertEqual(editor.command(), 'PLAN 15000 10000 3000 2000 3000 0')

    def test_read_only_without_a_session(self) -> None:
        editor = PlanEditor(Text('en'), 'SIG-01', {'a': 'N', 'b': 'E'})
        editor.set_writable(False)
        self.assertTrue(all(not box.isEnabled() for box in editor._boxes))


class FakeReply(QObject):
    """Stands in for QNetworkReply: a finished signal and a status attribute."""

    finished = pyqtSignal()

    def __init__(self, status: int | None) -> None:
        super().__init__()
        self._status = status

    def attribute(self, which: QNetworkRequest.Attribute) -> int | None:
        assert which is QNetworkRequest.Attribute.HttpStatusCodeAttribute
        return self._status


class FakeApi:
    """Records the staff request the sender makes."""

    def __init__(self, status: int | None) -> None:
        self.calls: list[tuple[str, Any, bool]] = []
        self.reply = FakeReply(status)

    def web_request(self, path: str, data: Any, *, authenticated: bool) -> FakeReply:
        self.calls.append((path, data, authenticated))
        return self.reply


class SignalCommandSenderTest(unittest.TestCase):
    """Commands go to the staff endpoint with the FMS session."""

    def test_posts_the_command_and_reports_the_outcome(self) -> None:
        for status, key in ((202, 'signal_queued'), (None, 'signal_send_failed')):
            api = FakeApi(status)
            results: list[str] = []
            SignalCommandSender(api).send('SIG-01', 'AUTO', results.append)  # type: ignore[arg-type]
            api.reply.finished.emit()
            self.assertEqual(
                api.calls, [('/api/signals/SIG-01/commands', {'command': 'AUTO'}, True)]
            )
            self.assertEqual(results, [key])


class SignalMapTest(unittest.TestCase):
    """The centre intersection is one click target for both heads."""

    def test_clicking_the_intersection_opens_its_signal(self) -> None:
        opened: list[str] = []
        board = SignalMap(
            DEFAULT_MAP_ROOT / 'amo-map-confirmed.png', 'map', 'missing', opened.append
        )
        board.resize(800, 730)
        board.show()
        APP.processEvents()
        self.assertEqual(board.hit(QPointF(396, 400)), 'SIG-01')  # inside the "+"
        self.assertEqual(
            board.hit(QPointF(427, 220)), 'SIG-01'
        )  # head a over northbound lanes
        self.assertEqual(
            board.hit(QPointF(481, 466)), 'SIG-01'
        )  # head b over eastbound lanes
        self.assertEqual(board.hit(QPointF(40, 40)), '')
        board.close()

    def test_red_hangs_at_each_drivers_left(self) -> None:
        sig01, sig02, sig03, sig04 = INTERSECTIONS
        self.assertTrue(sig03.a.pedestrian and sig04.a.pedestrian)
        self.assertEqual((sig03.b.horizontal, sig03.b.reverse), (False, False))
        # westbound, pole at the driver's left: red at the bottom (south)
        self.assertEqual((sig04.b.horizontal, sig04.b.reverse), (False, True))
        # (horizontal, reverse): red left, top, right, bottom on the map.
        self.assertEqual((sig01.a.horizontal, sig01.a.reverse), (True, False))
        self.assertEqual((sig01.b.horizontal, sig01.b.reverse), (False, False))
        self.assertEqual((sig02.a.horizontal, sig02.a.reverse), (True, True))
        self.assertEqual((sig02.b.horizontal, sig02.b.reverse), (False, True))


if __name__ == '__main__':
    unittest.main()
