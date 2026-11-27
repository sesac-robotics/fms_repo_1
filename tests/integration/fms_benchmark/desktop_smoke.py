"""Smoke-test the real browser-to-Qt staff sign-in and native workspace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal
from unittest.mock import patch

from amo_fms.admin import AdminApplication
from amo_fms.config import Config, Preferences
from amo_fms.main import Application
from PyQt6.QtCore import QSettings, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QTabWidget

HERE = Path(__file__).resolve().parent


def check_client(client: Literal['fms', 'admin'], output: Path) -> int:
    """Verify one desktop login and initial workspace, saving a local capture."""
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    settings = QSettings(str(output / f'{client}.ini'), QSettings.Format.IniFormat)
    settings.setValue('walkthrough/enabled', False)
    config = Config.from_environment(fleet=client == 'fms')
    if client == 'fms':
        window = Application(config, Preferences(settings))
        start_login = window._start_browser_login
    else:
        window = AdminApplication(config, Preferences(settings))
        start_login = window._sign_in
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
        if isinstance(window, Application):
            expected = {f'PINKY-{number:02d}' for number in range(1, 5)}
            visible = {vehicle.number for vehicle in window._snapshot.vehicles}
            ready = expected.issubset(visible)
        else:
            tabs = window.centralWidget().findChild(QTabWidget)
            expected_tabs = 9 if config.scenario_review else 8
            ready = tabs is not None and tabs.count() == expected_tabs
        if not ready:
            return
        if not window.grab().save(str(output / f'desktop-{client}.png')):
            app.exit(1)
            return
        print(f'{client}: browser sign-in and initial workspace verified.')
        app.quit()

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(250)
    QTimer.singleShot(25_000, lambda: app.exit(1))
    with patch.object(QDesktopServices, 'openUrl', open_browser):
        QTimer.singleShot(0, start_login)
        status = app.exec()
    if browser is not None and browser.poll() is None:
        browser.terminate()
        browser.wait(timeout=5)
    return status


def main() -> int:
    """Run each desktop smoke check in a separate Qt process by default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--client', choices=('fms', 'admin'))
    args = parser.parse_args()
    if args.client is not None:
        return check_client(args.client, args.output)
    for client in ('fms', 'admin'):
        result = subprocess.run(
            [sys.executable, __file__, str(args.output), '--client', client],
            check=False,
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
