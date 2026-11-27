"""Click the native review tab against a running isolated demo gateway."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton

from amo_fms.admin import AdminApplication
from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.confirmed_review_map import ConfirmedReviewMap
from amo_fms.main import Application
from amo_fms.review_lanes import DEPOT, S2
from amo_fms.scenario_review_panel import ScenarioReviewPanel

DEMO_HTTP = os.environ.get('AMO_DEMO_HTTP', '')


@unittest.skipUnless(
    DEMO_HTTP.startswith('http://127.0.0.1:'), 'requires a local demo server'
)
class ScenarioReviewPanelTest(unittest.TestCase):
    """Exercise native playback controls and the independent FMS map view."""

    def test_native_case_buttons_confirmed_map_and_reset(self) -> None:
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / 'review.ini'), QSettings.Format.IniFormat
            )
            settings.setValue('walkthrough/enabled', False)
            settings.setValue('language', 'en')
            config = Config(
                DEMO_HTTP,
                DEFAULT_MAP_ROOT,
                operations_port=int(os.environ.get('AMO_DEMO_IF03_PORT', '18087')),
                scenario_review=True,
            )
            window = AdminApplication(config, Preferences(settings))
            fms = Application(config, Preferences(settings))
            window.show()
            fms.show()
            try:
                self._review_case(window, fms)
            finally:
                fms.close()
                window.close()
                app.processEvents()

    def _review_case(self, window: AdminApplication, fms: Application) -> None:
        window._api.login('admin@amo.test', 'AmoDemo!2026')
        fms._api.login('admin@amo.test', 'AmoDemo!2026')
        self.wait(lambda: window.findChild(ScenarioReviewPanel) is not None)
        self.wait(lambda: fms.findChild(ConfirmedReviewMap) is not None)
        review = window.findChild(ScenarioReviewPanel)
        board = fms.findChild(ConfirmedReviewMap)
        assert (
            review is not None and window._workspace is not None and board is not None
        )
        window._workspace.setCurrentWidget(review)
        self.wait(lambda: review._plan.count() == 2)
        review._plan.setCurrentIndex(0)
        QTest.mouseClick(review._start, Qt.MouseButton.LeftButton)
        self.wait(lambda: self.ready(review, 'INITIAL_OCCUPY'))
        self.wait(lambda: board._review is not None and board._point == DEPOT)
        artwork = board.pixmap()
        self.assertIsNotNone(artwork)
        assert artwork is not None
        self.assertFalse(artwork.isNull())
        plan = review._session.plans[0]
        review._list.setCurrentRow(plan.steps.index('ROUTE_APPLIED'))
        QTest.mouseClick(review._jump, Qt.MouseButton.LeftButton)
        self.wait(lambda: self.ready(review, 'ROUTE_APPLIED'))
        failed = next(
            option
            for option in review.findChildren(QPushButton)
            if option.isVisible() and option.text() == 'Report IF-04 route failure'
        )
        QTest.mouseClick(failed, Qt.MouseButton.LeftButton)
        self.wait(lambda: self.ready(review, 'REDEPART'))
        self.assertIn('DEMO_ROUTE_FAILED', review._observed.toPlainText())
        self.assertIn('Effective stop · S2', review._observed.toPlainText())
        self.click_step(review, review._steps.index('REDEPART'))
        self.wait(lambda: self.ready(review, 'DESTINATION_STOP'))
        self.wait(lambda: board._point == S2 and not board._clock.isActive())
        QTest.mouseClick(review._reset_current, Qt.MouseButton.LeftButton)
        self.wait(lambda: review._session.run is None and board._review is None)
        confirmed = self._confirm_history_reset(review)
        self.wait(lambda: bool(confirmed) and not review._session.busy)
        self.assertEqual(review._notice.text(), 'Review reset completed.')

    @staticmethod
    def _confirm_history_reset(review: ScenarioReviewPanel) -> list[str]:
        confirmed: list[str] = []

        def confirm() -> None:
            for dialog in review.findChildren(QMessageBox):
                if dialog.isVisible():
                    yes = dialog.button(QMessageBox.StandardButton.Yes)
                    if yes is not None:
                        confirmed.append(dialog.text())
                        yes.click()

        timer = QTimer(review)
        timer.setInterval(10)
        timer.timeout.connect(confirm)
        timer.start()
        review._session.changed.connect(timer.stop)
        QTest.mouseClick(review._reset_history, Qt.MouseButton.LeftButton)
        return confirmed

    @staticmethod
    def click_step(panel: ScenarioReviewPanel, row: int) -> None:
        """Click a visible list item using the same signal as the reviewer."""
        item = panel._list.item(row)
        panel._list.scrollToItem(item)
        QTest.mouseClick(
            panel._list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=panel._list.visualItemRect(item).center(),
        )

    @staticmethod
    def ready(panel: ScenarioReviewPanel, target: str) -> bool:
        """Report when the server cursor reaches a step and the client has no pending reply."""
        run = panel._session.run
        return run is not None and run.next_step == target and not panel._session.busy

    def wait(self, condition: Callable[[], bool]) -> None:
        """Dispatch Qt events until the local action completes or the test times out."""
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if condition():
                return
            QTest.qWait(20)
        self.fail('Review UI did not reach the expected state.')
