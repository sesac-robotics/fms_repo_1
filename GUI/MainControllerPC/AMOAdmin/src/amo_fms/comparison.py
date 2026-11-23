"""Separate entry point for the one-process comparison."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSplitter

from .admin_workspace import AdminWorkspace
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
        tabs = AdminWorkspace(
            self._api,
            self._operator.role,
            self._config,
            self._prefs,
            self._settings,
            panel,
        )
        self._admin_operations = tabs.operations
        tabs.operations.present(self._snapshot)
        panel.addWidget(tabs)
        panel.setStretchFactor(0, 3)
        panel.setStretchFactor(1, 2)
        self.setCentralWidget(panel)
        tabs.load()

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
