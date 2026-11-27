"""Entry point for the independent AMO administrator process."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from .admin import AdminApplication
from .config import Config, Preferences
from .tls_trust import configure_classroom_trust


def main() -> int:
    """Start the staff-only process and its separate preference profile."""
    app = QApplication(sys.argv)
    configure_classroom_trust()
    app.setApplicationName('AMO Admin')
    prefs = Preferences(QSettings('AMoDE', 'AMO-Admin'))
    window = AdminApplication(Config.from_environment(fleet=False), prefs)
    window.show()
    return app.exec()
