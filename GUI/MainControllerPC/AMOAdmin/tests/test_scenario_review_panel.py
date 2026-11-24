"""Click the native review tab against a running isolated demo gateway."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QTableWidget

from amo_fms.admin import AdminApplication
from amo_fms.config import DEFAULT_MAP_ROOT, Config, Preferences
from amo_fms.scenario_review_panel import ScenarioReviewPanel

DEMO_HTTP = os.environ.get('AMO_DEMO_HTTP', '')


@unittest.skipUnless(
    DEMO_HTTP.startswith('http://127.0.0.1:'), 'requires a local demo server'
)
class ScenarioReviewPanelTest(unittest.TestCase):
    """Exercise jump, single-step clicks, stored evidence and the existing history view."""

    def test_click_paid_failure_and_open_ride_history(self) -> None:
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / 'review.ini'), QSettings.Format.IniFormat
            )
            settings.setValue('walkthrough/enabled', False)
            settings.setValue('language', 'en')
            window = AdminApplication(
                Config(DEMO_HTTP, DEFAULT_MAP_ROOT, scenario_review=True),
                Preferences(settings),
            )
            window.show()
            try:
                window._api.login('admin@amo.test', 'AmoDemo!2026')
                self.wait(lambda: window.findChild(ScenarioReviewPanel) is not None)
                review = window.findChild(ScenarioReviewPanel)
                assert review is not None and window._workspace is not None
                window._workspace.setCurrentWidget(review)
                self.wait(lambda: review._plan.count() == 2)
                plan = next(
                    p for p in review._session.plans if p.id == 'TAXI_APPLY_FAILED'
                )
                review._plan.setCurrentIndex(review._session.plans.index(plan))
                row = plan.steps.index('ROUTE_FAILED')
                review._list.setCurrentRow(row)
                QTest.mouseClick(review._jump, Qt.MouseButton.LeftButton)
                self.wait(lambda: self.ready(review, 'ROUTE_FAILED'))
                run = review._session.run
                assert run is not None
                self.assertEqual(len(run.completed), row)
                item = review._list.item(row)
                review._list.scrollToItem(item)
                point = review._list.visualItemRect(item).center()
                QTest.mouseClick(
                    review._list.viewport(), Qt.MouseButton.LeftButton, pos=point
                )
                self.wait(lambda: self.ready(review, 'DESTINATION_STOP'))
                self.assertIn('DEMO_ROUTE_FAILED', review._observed.toPlainText())
                self.assertIn('Effective stop · S2', review._observed.toPlainText())
                review._list.setCurrentRow(plan.steps.index('CHANGE_ACCEPT'))
                self.assertIn(
                    'MOCK_DIFFERENCE_ATTEMPTED', review._observed.toPlainText()
                )
                self.assertFalse(review._play.isEnabled())
                QTest.mouseClick(review._history, Qt.MouseButton.LeftButton)
                history = window._workspace.currentWidget()
                assert history is not None
                table = history.findChild(QTableWidget)
                self.wait(lambda: table is not None and table.rowCount() > 0)
                assert table is not None
                self.assertEqual(table.item(0, 0).text(), str(run.request_id))
            finally:
                window.close()
                app.processEvents()

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
