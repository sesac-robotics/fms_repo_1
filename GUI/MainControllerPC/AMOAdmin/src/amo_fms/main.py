"""AMO FMS application entry point and session coordination."""

from __future__ import annotations

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow

from .api import PreviewApi
from .config import Config, Preferences
from .desktop_sign_in import DesktopSignIn
from .i18n import Text
from .login_page import LoginPage
from .models import Operator, Snapshot
from .preferences_dialog import PreferenceDialog
from .theme import palette, stylesheet
from .tutorial import Walkthrough
from .workspace import Workspace


class Application(QMainWindow):
    """Route UI events to a preview API without owning business state transitions."""

    def __init__(self, config: Config, prefs: Preferences) -> None:
        """Load display settings and create the unsigned-in operator view."""
        super().__init__()
        self._config = config
        self._prefs = prefs
        self._operator: Operator | None = None
        self._snapshot = Snapshot()
        self._selected_id = ''
        self._page = 'monitor'
        self._status_key = 'snapshot_wait'
        self._seen_at = ''
        self._login_notice = ''
        self._login_pending = False
        self._login: LoginPage | None = None
        self._workspace: Workspace | None = None
        self._api = PreviewApi(config.endpoint, config.operations_port, self)
        self._api.authenticated.connect(self._signed_in)
        self._api.failed.connect(self._error)
        self._api.snapshot_received.connect(self._received)
        self._api.session_ended.connect(self._signed_out)
        self._browser = DesktopSignIn(config.admin_web, self)
        self._browser.ready.connect(self._redeem_browser_code)
        self._browser.failed.connect(self._tell_login)
        self._timer = QTimer(self)
        self._timer.setInterval(7500)
        self._timer.timeout.connect(self._api.refresh)
        self.setMinimumSize(920, 650)
        self.resize(1220, 855)
        self._build()

    @property
    def tr(self) -> Text:
        """Use the active UI language for all chrome and local messages."""
        return Text(self._prefs.language)

    def _build(self) -> None:
        tr = self.tr
        self.setWindowTitle(tr('apptitle'))
        self.setStyleSheet(stylesheet(palette(self._prefs.theme)))
        if self._operator is None:
            self._workspace = None
            self._login = LoginPage(tr, self._config, self._prefs)
            self._login.login_requested.connect(self._start_browser_login)
            self._login.cancel_requested.connect(self._cancel_browser_login)
            self._login.preference_changed.connect(self._change_preference)
            self.setCentralWidget(self._login)
            self._login.tell(self._login_notice, pending=self._login_pending)
        else:
            self._login = None
            self._workspace = Workspace(
                tr, self._config, self._prefs, self._operator, self._page
            )
            self._workspace.request_settings.connect(self._settings)
            self._workspace.request_logout.connect(self._api.logout)
            self._workspace.request_refresh.connect(self._api.refresh)
            self._workspace.vehicle_selected.connect(self._select)
            self._workspace.page_selected.connect(self._select_page)
            self.setCentralWidget(self._workspace)
            self._workspace.show_snapshot(self._snapshot, self._selected_id)
            self._present_status()

    def _change_preference(self, key: str, value: str) -> None:
        self._prefs.settings.setValue(key, value)
        self._build()

    def _tell_login(self, notice: str, pending: bool = False) -> None:
        self._login_notice = notice
        self._login_pending = pending
        if self._login is not None:
            self._login.tell(notice, pending)

    def _start_browser_login(self) -> None:
        self._tell_login('browser_wait', pending=True)
        self._browser.start(self.tr('browser_return'))

    def _redeem_browser_code(self, port: int, code: str, verifier: str) -> None:
        self._tell_login('working', pending=True)
        self._api.login_desktop(port, code, verifier)

    def _cancel_browser_login(self) -> None:
        self._browser.cancel()
        self._api.cancel_login()
        self._tell_login('browser_cancelled')

    def _signed_in(self, operator: Operator) -> None:
        self._operator = operator
        self._tell_login('')
        self._build()
        self._timer.start()
        self._api.refresh()
        if self._prefs.should_offer_walkthrough:
            QTimer.singleShot(90, self._walkthrough)

    def _signed_out(self, notice: str) -> None:
        self._operator = None
        self._snapshot = Snapshot()
        self._selected_id = ''
        self._page = 'monitor'
        self._status_key = 'snapshot_wait'
        self._seen_at = ''
        self._timer.stop()
        self._browser.cancel()
        self._tell_login(notice)
        self._build()

    def _select(self, vehicle_id: str) -> None:
        self._selected_id = vehicle_id

    def _select_page(self, page: str) -> None:
        self._page = page
        if self._workspace is not None:
            self._workspace.show_snapshot(self._snapshot, self._selected_id)

    def _received(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot
        if not any(v.id == self._selected_id for v in snapshot.vehicles):
            self._selected_id = snapshot.vehicles[0].id if snapshot.vehicles else ''
        self._seen_at = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%H:%M:%S')
        self._status_key = 'snapshot_at'
        if self._workspace is not None:
            self._workspace.show_snapshot(snapshot, self._selected_id)
            self._present_status()

    def _error(self, category: str, key: str) -> None:
        if category == 'login':
            self._tell_login(key)
        else:
            self._status_key = key
            self._present_status()

    def _present_status(self) -> None:
        if self._workspace is not None:
            text = self.tr(self._status_key, time=self._seen_at)
            if self._status_key == 'snapshot_unavailable' and self._seen_at:
                text += ' · ' + self.tr('snapshot_at', time=self._seen_at)
            self._workspace.tell(text)

    def _settings(self) -> None:
        dialog = PreferenceDialog(self.tr, self._prefs, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._build()
            if dialog.replay:
                self._walkthrough()

    def _walkthrough(self) -> None:
        if self._operator is not None:
            Walkthrough(self.tr, self._prefs, self).exec()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Cancel the listener and token reply before releasing Qt resources."""
        self._browser.cancel()
        self._api.cancel_login()
        self._timer.stop()
        super().closeEvent(event)


def main() -> int:
    """Run the PyQt FMS development client."""
    app = QApplication(sys.argv)
    app.setApplicationName('AMO FMS')
    window = Application(Config.from_environment(), Preferences.open())
    window.show()
    return app.exec()
