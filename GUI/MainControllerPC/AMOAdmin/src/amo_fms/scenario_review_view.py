"""Lay out the review controls and evidence fields."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

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
from .scenario_review_labels import step_title
from .scenario_review_wire import Plan, Run


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
        self._evidence_only = QCheckBox(tr('review_evidence_only'))
        self._play = QPushButton(tr('review_play'))
        self._start = QPushButton(tr('review_start'))
        self._jump = QPushButton(tr('review_jump'))
        self._reload = QPushButton(tr('refresh'))
        self._history = QPushButton(tr('review_history'))
        self._reset_current = QPushButton(tr('review_reset_current'))
        self._reset_history = QPushButton(tr('review_reset_history'))
        self._cases = QHBoxLayout()
        self._displayed_cases: tuple[str, ...] = ()
        self._build()

    def _build(self) -> None:
        tr = self._tr
        root = QVBoxLayout(self)
        start = QHBoxLayout()
        for widget in (self._plan, self._start, self._jump, self._reload):
            start.addWidget(widget, 1 if widget is self._plan else 0)
        root.addLayout(start)
        root.addWidget(self._summary)
        resets = QHBoxLayout()
        for widget in (self._history, self._reset_current, self._reset_history):
            resets.addWidget(widget)
        root.addLayout(resets)
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
        actions.addStretch(1)
        right.addLayout(actions)
        right.addLayout(self._cases)
        splitter.addWidget(detail)
        splitter.setSizes([340, 540])
        root.addWidget(splitter, 1)
        root.addWidget(self._notice)

    def show_cases(
        self,
        steps: tuple[str, ...],
        enabled: bool,
        choose: Callable[[str], None],
    ) -> None:
        """Show only the contextual choices the server accepts for this run."""
        if steps != self._displayed_cases:
            self._displayed_cases = steps
            while self._cases.count():
                item = self._cases.takeAt(0)
                widget = item.widget() if item is not None else None
                if widget is not None:
                    widget.deleteLater()
            for step in steps:
                option = QPushButton(
                    self._tr('review_case_prepay')
                    if step == 'PREPAY'
                    else step_title(self._tr, step)
                )
                option.clicked.connect(partial(choose, step))
                self._cases.addWidget(option)
        for i in range(self._cases.count()):
            item = self._cases.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setEnabled(enabled)


def review_choices(run: Run | None) -> tuple[str, ...]:
    """Separate branching and recovery choices from the ordinary next-step button."""
    if run is None or not run.available:
        return ()
    if len(run.available) > 1 or run.available[0] in {
        'LINK_RESTORED',
        'RESUME_APPROVED',
        'PREPAY',
        'REDEPART',
    }:
        return run.available
    return ()


def display_steps(plan: Plan | None, run: Run | None) -> tuple[str, ...]:
    """Keep committed alternatives in order and retain future catalog stages."""
    if plan is None:
        return ()
    if run is None:
        return plan.steps
    seen = tuple(run.completed)
    future = [step for step in plan.steps if step not in seen]
    if 'ROUTE_APPLIED' in seen or 'ROUTE_FAILED' in seen:
        future = [
            step for step in future if step not in {'ROUTE_APPLIED', 'ROUTE_FAILED'}
        ]
    return tuple(dict.fromkeys((*seen, *run.available, *future)))
