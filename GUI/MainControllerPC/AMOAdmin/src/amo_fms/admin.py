"""Run the staff workspace as an independent desktop application."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from .admin_operations import OperationsRead
from .admin_workspace import AdminWorkspace
from .config import Config, Preferences
from .desktop_sign_in import DesktopSignIn
from .i18n import Text
from .login_page import LoginPage
from .models import Operator, Snapshot
from .preferences_dialog import PreferenceDialog
from .staff_api import StaffApi
from .theme import palette, stylesheet
from .tutorial import Walkthrough
from .widgets import button, label

ADMIN_STEPS = (
    ('admin_overview_title', 'admin_tutorial_overview'),
    ('admin_history_title', 'admin_tutorial_history'),
    ('settings', 'tutorial_settings'),
)


class AdminApplication(QMainWindow):
    """Own an independent staff session and pull operational views on demand."""

    def __init__(self, config: Config, prefs: Preferences) -> None:
        """Create the Web-only desktop window and its browser login bridge."""
        super().__init__()
        self._config = config
        self._prefs = prefs
        self._api = StaffApi(config.endpoint, self)
        self._browser = DesktopSignIn(config.admin_web, self)
        self._operator: Operator | None = None
        self._login: LoginPage | None = None
        self._workspace: AdminWorkspace | None = None
        self._operations = OperationsRead(self._api, self)
        self._operations.received.connect(self._present_operations)
        self._operations.failed.connect(self._operations_failed)
        self._notice = ''
        self._pending = False
        self._snapshot = Snapshot()
        self._api.authenticated.connect(self._signed_in)
        self._api.failed.connect(self._login_error)
        self._api.session_ended.connect(self._signed_out)
        self._browser.ready.connect(self._redeem)
        self._browser.failed.connect(self._tell_login)
        self.setWindowTitle('AMO Admin')
        self.resize(1050, 720)
        self._build()

    @property
    def text(self) -> Text:
        """Return the active display language."""
        return Text(self._prefs.language)

    def _build(self) -> None:
        self._operations.cancel()
        self.setStyleSheet(stylesheet(palette(self._prefs.theme)))
        if self._operator is None:
            self._workspace = None
            self._login = LoginPage(self.text, self._config, self._prefs)
            self._login.login_requested.connect(self._sign_in)
            self._login.cancel_requested.connect(self._cancel_sign_in)
            self._login.preference_changed.connect(self._change_preference)
            self.setCentralWidget(self._login)
            self._login.tell(self._notice, pending=self._pending)
            return

        self._login = None
        shell = QWidget()
        layout = QVBoxLayout(shell)
        controls = QHBoxLayout()
        controls.addWidget(
            label(self._operator.name or self._operator.email, 'heading')
        )
        controls.addStretch()
        self._refresh_button = button(self.text('refresh'))
        self._refresh_button.clicked.connect(self._load_operations)
        controls.addWidget(self._refresh_button)
        logout = button(self.text('sign_out'))
        logout.clicked.connect(self._api.logout)
        controls.addWidget(logout)
        layout.addLayout(controls)
        self._status = label('', 'secondary')
        layout.addWidget(self._status)
        self._workspace = AdminWorkspace(
            self._api,
            self._operator.role,
            self._config,
            self._prefs,
            self._settings,
            shell,
        )
        self._workspace.operations.present(self._snapshot)
        layout.addWidget(self._workspace, 1)
        self.setCentralWidget(shell)
        self._workspace.currentChanged.connect(self._menu_changed)
        self._menu_changed(self._workspace.currentIndex())
        self._workspace.load()

    def _menu_changed(self, index: int) -> None:
        if self._workspace is None:
            return
        key = self._workspace.tabBar().tabData(index) if index >= 0 else None
        visible = key in {'overview', 'logs'}
        self._refresh_button.setVisible(visible)
        self._status.setVisible(visible)
        if visible:
            self._load_operations()
        else:
            self._operations.cancel()

    def _load_operations(self) -> None:
        if self._workspace is not None and self._operations.load():
            self._status.setText(self.text('working'))

    def _present_operations(self, snapshot: Snapshot) -> None:
        if self._workspace is not None:
            self._snapshot = snapshot
            self._workspace.operations.present(snapshot)
            self._status.clear()

    def _operations_failed(self) -> None:
        if self._workspace is not None:
            self._status.setText(self.text('snapshot_unavailable'))

    def _tell_login(self, notice: str, pending: bool = False) -> None:
        self._notice, self._pending = notice, pending
        if self._login is not None:
            self._login.tell(notice, pending=pending)

    def _sign_in(self) -> None:
        self._tell_login('browser_wait', pending=True)
        self._browser.start(self.text('admin_browser_return'))

    def _redeem(self, port: int, code: str, verifier: str) -> None:
        self._tell_login('working', pending=True)
        self._api.login_desktop(port, code, verifier)

    def _cancel_sign_in(self) -> None:
        self._browser.cancel()
        self._api.cancel_login()
        self._tell_login('browser_cancelled')

    def _login_error(self, _category: str, key: str) -> None:
        self._tell_login(key)

    def _signed_in(self, operator: Operator) -> None:
        self._operator = operator
        self._tell_login('')
        self._build()
        if self._prefs.should_offer_walkthrough:
            QTimer.singleShot(90, self._walkthrough)

    def _signed_out(self, notice: str) -> None:
        self._operator = None
        self._snapshot = Snapshot()
        self._tell_login(notice)
        self._build()

    def _change_preference(self, key: str, value: str) -> None:
        self._prefs.settings.setValue(key, value)
        self._build()

    def _settings(self) -> None:
        dialog = PreferenceDialog(self.text, self._prefs, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._build()
            if dialog.replay:
                self._walkthrough()

    def _walkthrough(self) -> None:
        if self._operator is not None:
            Walkthrough(self.text, self._prefs, self, steps=ADMIN_STEPS).exec()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Cancel pending local requests while closing the independent window."""
        self._browser.cancel()
        self._api.cancel_login()
        self._operations.cancel()
        super().closeEvent(event)
