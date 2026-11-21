"""Read-only operations data and a clearly isolated vehicle-action preview."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .i18n import Text, display_time
from .models import Snapshot, Vehicle
from .widgets import button, label, panel

ACTIONS = ('move', 'hold', 'resume', 'return_depot')


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
            ('request_id', 'pickup', 'destination', 'status')
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
                (r.id, r.pickup, r.destination, tr.status(r.status))
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


class ActionsPage(QWidget):
    """Review a request for one vehicle with no network or motion side effects."""

    def __init__(self, tr: Text, select: Callable[[str], None]) -> None:
        """Build vehicle and action selectors plus an explicit warning."""
        super().__init__()
        self._tr = tr
        self._select = select
        self._vehicles: tuple[Vehicle, ...] = ()
        self._selection: Vehicle | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card, body = panel()
        body.addWidget(label(tr('action_caption'), 'secondary'))
        self._vehicle = QComboBox()
        self._vehicle.setAccessibleName(tr('vehicle_no'))
        self._vehicle.currentIndexChanged.connect(self._vehicle_changed)
        body.addWidget(label(tr('vehicle_no'), 'heading'))
        body.addWidget(self._vehicle)
        self._connected = label(tr('select_hint'), 'secondary')
        body.addWidget(self._connected)
        body.addWidget(label(tr('action_label'), 'heading'))
        self._action = QComboBox()
        self._action.setAccessibleName(tr('action_label'))
        for name in ACTIONS:
            self._action.addItem(tr(name), name)
        body.addWidget(self._action)
        self._inspect = button(tr('draft'), 'primary')
        self._inspect.setEnabled(False)
        self._inspect.clicked.connect(self._review)
        body.addWidget(self._inspect)
        self._result = label('', 'warning')
        body.addWidget(self._result)
        outer.addWidget(card)
        outer.addStretch(1)

    def show_snapshot(self, snapshot: Snapshot, selected_id: str) -> None:
        """Enable preview for a connected or explicitly simulated vehicle."""
        self._vehicle.blockSignals(True)
        if self._vehicles != snapshot.vehicles:
            self._vehicles = snapshot.vehicles
            self._vehicle.clear()
            self._vehicle.addItem(self._tr('select_hint'), '')
            for v in self._vehicles:
                self._vehicle.addItem(v.number, v.id)
        self._vehicle.setCurrentIndex(max(0, self._vehicle.findData(selected_id)))
        self._vehicle.blockSignals(False)
        self._update_selection(selected_id)

    def _vehicle_changed(self, _index: int) -> None:
        selected = self._vehicle.currentData() or ''
        self._update_selection(selected)
        self._select(selected)

    def _update_selection(self, selected_id: str) -> None:
        self._selection = next((v for v in self._vehicles if v.id == selected_id), None)
        can_preview = self._selection is not None and self._selection.can_preview
        self._inspect.setEnabled(can_preview)
        if can_preview:
            self._connected.setText(self._tr('action_details'))
        else:
            self._connected.setText(self._tr('offline_action'))

    def _review(self) -> None:
        current = self._selection
        if current is None or not current.can_preview:
            return
        tr = self._tr
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('preview_request'))
        content = QVBoxLayout(dialog)
        content.addWidget(label(tr('preview_confirm', vehicle=current.number)))
        actions = QHBoxLayout()
        cancel = button(tr('cancel'))
        confirm = button(tr('confirm'), 'primary')
        cancel.clicked.connect(dialog.reject)
        confirm.clicked.connect(dialog.accept)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(confirm)
        content.addLayout(actions)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._result.setText(
                tr(
                    'preview_result',
                    vehicle=current.number,
                    action=tr(self._action.currentData()),
                )
            )
