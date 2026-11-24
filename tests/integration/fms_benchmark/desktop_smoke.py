"""Smoke-test the real browser-to-Qt staff sign-in and native workspace."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from unittest.mock import patch

from amo_fms.comparison import ComparisonApplication
from amo_fms.config import Config, Preferences
from PyQt6.QtCore import QSettings, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QTabWidget

HERE = Path(__file__).resolve().parent


def main() -> int:
    """Use controlled Chrome navigation and save confirmation and a Qt capture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    settings = QSettings(str(args.output / 'desktop.ini'), QSettings.Format.IniFormat)
    settings.setValue('walkthrough/enabled', False)
    window = ComparisonApplication(Config.from_environment(), Preferences(settings))
    window.resize(1450, 800)
    window.show()
    browser: subprocess.Popen | None = None

    def open_browser(url: QUrl) -> bool:
        nonlocal browser
        browser = subprocess.Popen(
            ['node', str(HERE / 'desktop_signin.mjs'), url.toString()]
        )
        return True

    def check() -> None:
        if browser is None or browser.poll() is None:
            return
        if browser.returncode != 0:
            app.exit(1)
            return
        tabs = window.centralWidget().findChild(QTabWidget)
        expected = {f'PINKY-{number:02d}' for number in range(1, 5)}
        visible = {vehicle.number for vehicle in window._snapshot.vehicles}
        if tabs is None or tabs.count() != 8 or not expected.issubset(visible):
            return
        if not window.grab().save(str(args.output / 'desktop-comparison.png')):
            app.exit(1)
            return
        print(
            'Browser sign-in, eight admin tabs, and four Pinky IF-03 vehicle rows verified.'
        )
        app.quit()

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(250)
    QTimer.singleShot(25_000, lambda: app.exit(1))
    with patch.object(QDesktopServices, 'openUrl', open_browser):
        QTimer.singleShot(0, window._start_browser_login)
        status = app.exec()
    if browser is not None and browser.poll() is None:
        browser.terminate()
        browser.wait(timeout=5)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
