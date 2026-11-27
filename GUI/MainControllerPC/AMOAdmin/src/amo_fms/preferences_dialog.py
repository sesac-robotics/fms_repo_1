"""Editable display settings and manual tutorial replay."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from .config import Preferences
from .i18n import Text
from .widgets import button, language_select, theme_select


class PreferenceDialog(QDialog):
    """Commit changes only when the operator confirms them."""

    def __init__(self, tr: Text, prefs: Preferences, parent: QWidget) -> None:
        """Provide language, theme, and first-use walkthrough settings."""
        super().__init__(parent)
        self._prefs = prefs
        self.replay = False
        self.setWindowTitle(tr('settings'))
        self.setMinimumWidth(405)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        self._language = language_select(prefs.language, tr)
        self._theme = theme_select(prefs.theme, tr)
        form.addRow(tr('language'), self._language)
        form.addRow(tr('theme'), self._theme)
        layout.addLayout(form)
        self._first_use = QCheckBox(tr('tutorial_auto'))
        self._first_use.setChecked(prefs.walkthrough_enabled)
        layout.addWidget(self._first_use)
        replay = button(tr('tutorial_replay'))
        replay.clicked.connect(self._replay)
        layout.addWidget(replay)
        commands = QHBoxLayout()
        cancel = button(tr('cancel'))
        confirm = button(tr('confirm'), 'primary')
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        commands.addStretch(1)
        commands.addWidget(cancel)
        commands.addWidget(confirm)
        layout.addLayout(commands)

    def accept(self) -> None:
        """Save display and tutorial preferences to the current OS profile."""
        prefs = self._prefs.settings
        prefs.setValue('language', self._language.currentData())
        prefs.setValue('theme', self._theme.currentData())
        prefs.setValue('walkthrough/enabled', self._first_use.isChecked())
        super().accept()

    def _replay(self) -> None:
        self.replay = True
        self.accept()
