"""Localized FMS account login and visual preference entry points."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from .config import Config, Preferences
from .i18n import Text
from .widgets import brand, button, label, language_select, panel, theme_select


class LoginPage(QWidget):
    """Start browser authorization with the shared admin Web sign-in."""

    login_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    preference_changed = pyqtSignal(str, str)

    def __init__(self, tr: Text, config: Config, prefs: Preferences) -> None:
        """Construct a localized sign-in surface without storing credentials."""
        super().__init__()
        self._tr = tr
        shell = QHBoxLayout(self)
        shell.setContentsMargins(24, 20, 24, 20)
        shell.addStretch(1)
        column = QVBoxLayout()
        column.addStretch(1)
        card, content = panel('loginCard')
        content.setContentsMargins(27, 26, 27, 26)
        content.setSpacing(14)
        card.setMinimumWidth(390)
        card.setMaximumWidth(510)
        content.addWidget(brand(config, prefs.theme, 160))
        content.addWidget(label(tr('operator_login'), 'title'))
        content.addWidget(label(tr('login_caption'), 'secondary'))
        self._signin = button(tr('sign_in'), 'primary')
        self._signin.clicked.connect(self.login_requested)
        self._cancel = button(tr('cancel'))
        self._cancel.clicked.connect(self.cancel_requested)
        self._cancel.hide()
        actions = QHBoxLayout()
        actions.addWidget(self._signin, 1)
        actions.addWidget(self._cancel)
        content.addLayout(actions)
        self._message = label('', 'warning')
        content.addWidget(self._message)
        preferences = QHBoxLayout()
        languages = language_select(prefs.language, tr)
        themes = theme_select(prefs.theme, tr)
        languages.currentIndexChanged.connect(
            lambda: self.preference_changed.emit('language', languages.currentData())
        )
        themes.currentIndexChanged.connect(
            lambda: self.preference_changed.emit('theme', themes.currentData())
        )
        preferences.addWidget(languages)
        preferences.addWidget(themes)
        content.addLayout(preferences)
        column.addWidget(card)
        column.addStretch(1)
        shell.addLayout(column, 2)
        shell.addStretch(1)

    def tell(self, message_key: str, pending: bool = False) -> None:
        """Show a localized outcome and prevent concurrent login attempts."""
        self._message.setText(self._tr(message_key) if message_key else '')
        self._signin.setEnabled(not pending)
        self._cancel.setVisible(pending)
