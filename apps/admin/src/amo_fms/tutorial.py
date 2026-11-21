"""First sign-in walkthrough and replay controls."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

from .config import Preferences
from .i18n import Text
from .widgets import button, label

STEPS = (
    ('monitor', 'tutorial_monitor'),
    ('queue', 'tutorial_queue'),
    ('events', 'tutorial_events'),
    ('settings', 'tutorial_settings'),
)


class Walkthrough(QDialog):
    """Show a bounded tutorial with back, next, skip, and dismissal."""

    def __init__(self, tr: Text, preferences: Preferences, parent: QWidget) -> None:
        """Initialize four locale-specific introductions to the operator workspace."""
        super().__init__(parent)
        self._tr = tr
        self._preferences = preferences
        self._index = 0
        self.setWindowTitle(tr('tutorial'))
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        self._heading = label('', 'heading')
        self._detail = label('')
        self._detail.setMinimumHeight(90)
        layout.addWidget(self._heading)
        layout.addWidget(self._detail)
        actions = QHBoxLayout()
        self._skip = button(tr('skip'))
        self._previous = button(tr('previous'))
        self._next = button(tr('next'), 'primary')
        self._skip.clicked.connect(self.reject)
        self._previous.clicked.connect(lambda: self._move(-1))
        self._next.clicked.connect(lambda: self._move(1))
        actions.addWidget(self._skip)
        actions.addStretch(1)
        actions.addWidget(self._previous)
        actions.addWidget(self._next)
        layout.addLayout(actions)
        self.finished.connect(self._seen)
        self._render()

    def _move(self, step: int) -> None:
        index = self._index + step
        if index == len(STEPS):
            self.accept()
        elif index >= 0:
            self._index = index
            self._render()

    def _render(self) -> None:
        title, body = STEPS[self._index]
        self._heading.setText(f'{self._index + 1}/{len(STEPS)} · {self._tr(title)}')
        self._detail.setText(self._tr(body))
        self._previous.setEnabled(self._index > 0)
        self._next.setText(
            self._tr('finish' if self._index == len(STEPS) - 1 else 'next')
        )

    def _seen(self, _result: int) -> None:
        self._preferences.settings.setValue('walkthrough/seen', True)
