"""Lay out the review controls and evidence fields."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .i18n import Text


class ReviewView(QWidget):
    """Keep the review list, controls and details in a resizable two-pane layout."""

    def __init__(self, tr: Text, parent: QWidget) -> None:
        """Construct the widgets for the scenario review presenter."""
        super().__init__(parent)
        self._tr = tr
        self._plan = QComboBox()
        self._plan.setAccessibleName(tr('review_plan'))
        self._list = QListWidget()
        self._list.setAccessibleName(tr('review_steps'))
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._expected = QLabel()
        self._expected.setWordWrap(True)
        self._observed = QTextEdit()
        self._observed.setAccessibleName(tr('review_observed'))
        self._observed.setReadOnly(True)
        self._notice = QLabel()
        self._notice.setWordWrap(True)
        self._manual = QCheckBox(tr('review_manual'))
        self._evidence_only = QCheckBox(tr('review_evidence_only'))
        self._play = QPushButton(tr('review_play'))
        self._start = QPushButton(tr('review_start'))
        self._jump = QPushButton(tr('review_jump'))
        self._reload = QPushButton(tr('refresh'))
        self._history = QPushButton(tr('review_open_ride'))
        self._build()

    def _build(self) -> None:
        tr = self._tr
        root = QVBoxLayout(self)
        start = QHBoxLayout()
        for widget in (self._plan, self._start, self._jump, self._reload):
            start.addWidget(widget, 1 if widget is self._plan else 0)
        root.addLayout(start)
        root.addWidget(self._summary)
        root.addWidget(self._manual)
        root.addWidget(self._evidence_only)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._list)
        detail = QWidget()
        right = QVBoxLayout(detail)
        right.addWidget(self._expected)
        right.addWidget(QLabel(tr('review_observed')))
        right.addWidget(self._observed, 1)
        actions = QHBoxLayout()
        actions.addWidget(self._play)
        actions.addWidget(self._history)
        right.addLayout(actions)
        splitter.addWidget(detail)
        splitter.setSizes([340, 540])
        root.addWidget(splitter, 1)
        root.addWidget(self._notice)
