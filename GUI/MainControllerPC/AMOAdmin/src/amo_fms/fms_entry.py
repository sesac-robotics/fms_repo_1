"""Application setup for the AMO FMS desktop process."""

import sys

from PyQt6.QtWidgets import QApplication

from .config import Config, Preferences
from .main import Application
from .tls_trust import configure_classroom_trust


def run() -> int:
    """Open the FMS window and run the Qt event loop."""
    app = QApplication(sys.argv)
    configure_classroom_trust()
    app.setApplicationName('AMO FMS')
    window = Application(Config.from_environment(), Preferences.open())
    window.show()
    return app.exec()
