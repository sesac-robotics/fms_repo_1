"""Separate entry point for the one-process comparison."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSplitter, QTabWidget

from .comparison_history import HistoryPanel
from .comparison_members import MembersPanel
from .comparison_menus import MenuPanel
from .comparison_operations import OperationTabs
from .config import Config, Preferences
from .main import Application
from .models import Snapshot


class ComparisonApplication(Application):
    """Keep the FMS visible beside administrative Web API views."""

    def _build(self) -> None:
        self._admin_operations: OperationTabs | None = None
        super()._build()
        if self._operator is None:
            return
        panel = QSplitter(Qt.Orientation.Horizontal)
        panel.addWidget(self.takeCentralWidget())
        tabs = QTabWidget(panel)
        if self._operator.role == 'ADMIN':
            tabs.addTab(MembersPanel(self._api, tabs), 'Members and roles')
        tabs.addTab(HistoryPanel(self._api, 'trip-history', tabs), 'Trip history')
        tabs.addTab(HistoryPanel(self._api, 'test-history', tabs), 'Test results')
        operations = OperationTabs(self.tr, self._settings)
        tabs.addTab(operations.overview, 'Overview')
        tabs.addTab(operations.logs, 'Operations log')
        tabs.addTab(operations.codes, 'Operation codes')
        if self._operator.role == 'ADMIN':
            tabs.addTab(MenuPanel(self._api, tabs), 'Menu management')
        tabs.addTab(operations.settings, 'Settings')
        self._admin_operations = operations
        operations.present(self._snapshot)
        panel.addWidget(tabs)
        panel.setStretchFactor(0, 3)
        panel.setStretchFactor(1, 2)
        self.setCentralWidget(panel)

    def _received(self, snapshot: Snapshot) -> None:
        super()._received(snapshot)
        if self._admin_operations is not None:
            self._admin_operations.present(snapshot)


def main() -> int:
    """Run the combined client with the same service configuration as the FMS."""
    app = QApplication(sys.argv)
    app.setApplicationName('AMO FMS')
    window = ComparisonApplication(Config.from_environment(), Preferences.open())
    window.resize(1650, 855)
    window.show()
    return app.exec()
