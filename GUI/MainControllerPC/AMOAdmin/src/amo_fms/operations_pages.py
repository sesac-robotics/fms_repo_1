"""Read-only operations data."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .i18n import Text, display_time
from .models import Snapshot
from .widgets import label, panel


class RecordsPage(QWidget):
    """Present request or event rows from an immutable backend snapshot."""

    def __init__(self, tr: Text, mode: str) -> None:
        """Build a read-only table, preserving backend event sequence."""
        super().__init__()
        self._tr = tr
        self._mode = mode
        self._rows: tuple[tuple[str, ...], ...] = ()
        body, pane = panel()
        caption = 'queue_caption' if mode == 'queue' else 'event_caption'
        pane.addWidget(label(tr(caption), 'secondary'))
        self._empty = label(tr('empty'), 'secondary')
        pane.addWidget(self._empty)
        headers = (
            ('request_id', 'pickup', 'destination', 'applied_route', 'status')
            if mode == 'queue'
            else ('event_time', 'event_type', 'vehicle_no', 'detail')
        )
        self._table = QTableWidget(0, len(headers))
        self._table.setAccessibleName(tr(mode))
        self._table.setHorizontalHeaderLabels([tr(k) for k in headers])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        pane.addWidget(self._table, 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body, 1)

    def show_snapshot(self, snapshot: Snapshot, _selected_id: str) -> None:
        """Refresh visible cells without promoting request events to actual state."""
        tr = self._tr
        if self._mode == 'queue':
            rows = tuple(
                (
                    r.id,
                    r.pickup,
                    r.destination,
                    f'{r.applied.destination} · #{r.applied.revision}'
                    if r.applied
                    else '—',
                    tr.status(r.status),
                )
                for r in snapshot.requests
            )
        else:
            rows = tuple(
                (
                    display_time(e.time),
                    tr.status(e.type),
                    e.vehicle or '—',
                    tr.event_detail(e.detail),
                )
                for e in snapshot.events
            )
        if rows == self._rows:
            return
        self._rows = rows
        self._empty.setVisible(not rows)
        self._table.setRowCount(len(rows))
        for r, records in enumerate(rows):
            for c, text in enumerate(records):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self._table.setItem(r, c, item)
