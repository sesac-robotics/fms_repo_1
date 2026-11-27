"""Paged read-only trip and test histories for the one-process comparison."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .comparison_route import RouteDialog
from .staff_api import StaffApi

FIELDS = {
    'trip-history': (
        'id',
        'serviceType',
        'status',
        'receivedAt',
        'prepaymentStatus',
        'routeStatus',
        'effectiveDestination',
        'appliedRevisionId',
        'differenceStatus',
        'finalAmountMinor',
        'currencyCode',
        'receiptReference',
        'depotPhase',
    ),
    'test-history': ('name', 'recordedAt', 'passed', 'total', 'latencyMs'),
}
HEADERS = {
    'trip-history': (
        'ID',
        'Service',
        'Status',
        'Received at',
        'Mock prepayment',
        'Route change',
        'Applied destination',
        'Applied revision',
        'Mock difference',
        'Final fare (minor units)',
        'Currency',
        'Receipt',
        'Depot phase',
    ),
    'test-history': ('Name', 'Recorded at', 'Passed', 'Total', 'Latency (ms)'),
}
PAGE_SIZE = 50


class HistoryPanel(QWidget):
    """Read page-sized staff history without interrupting IF-03 polling."""

    def __init__(
        self, api: StaffApi, resource: str, parent: QWidget, *, asset: str = ''
    ) -> None:
        """Use a staff session and a known operations history path."""
        super().__init__(parent)
        self._api = api
        self._resource = resource
        self._asset = asset
        self._reply: QNetworkReply | None = None
        self._offset = 0
        self._filters: dict[str, str] = {}
        body = QVBoxLayout(self)
        form = QFormLayout()
        self._inputs: dict[str, QLineEdit] = {}
        for key, label in (
            ('q', 'Search'),
            ('from', 'From date (UTC)'),
            ('until', 'Until date, exclusive (UTC)'),
        ):
            field = QLineEdit()
            field.setMaxLength(100 if key == 'q' else 10)
            if key != 'q':
                field.setPlaceholderText('YYYY-MM-DD')
            field.returnPressed.connect(self.search)
            form.addRow(label, field)
            self._inputs[key] = field
        body.addLayout(form)
        controls = QHBoxLayout()
        search = QPushButton('Search')
        search.clicked.connect(self.search)
        controls.addWidget(search)
        self._previous = QPushButton('Previous')
        self._previous.clicked.connect(lambda: self.load(self._offset - PAGE_SIZE))
        self._next = QPushButton('Next')
        self._next.clicked.connect(lambda: self.load(self._offset + PAGE_SIZE))
        for button in (self._previous, self._next):
            controls.addWidget(button)
            button.setEnabled(False)
        body.addLayout(controls)
        self._status = QLabel()
        body.addWidget(self._status)
        self._table = QTableWidget(0, len(FIELDS[resource]))
        self._table.setHorizontalHeaderLabels(HEADERS[resource])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        body.addWidget(self._table)
        if resource == 'trip-history':
            route = QPushButton('Open selected recorded route')
            route.clicked.connect(self._route)
            body.addWidget(route)

    def _route(self) -> None:
        item = self._table.item(self._table.currentRow(), 0)
        if item is not None and item.text().isdigit():
            RouteDialog(self._api, int(item.text()), self._asset, self).show()

    def show_request(self, request_id: int) -> None:
        """Find a review's exact positive request ID without old date filters."""
        for field in self._inputs.values():
            field.clear()
        self._inputs['q'].setText(str(request_id))
        self.search()

    def search(self) -> None:
        """Apply search and half-open UTC date filters starting on the first page."""
        self._filters = {'q': self._inputs['q'].text().strip()}
        for key in ('from', 'until'):
            if value := self._inputs[key].text().strip():
                self._filters[key] = f'{value}T00:00:00Z'
        self.load(0)

    def load(self, offset: int) -> None:
        """Fetch a new page and discard any superseded reply."""
        if self._reply is not None:
            previous, self._reply = self._reply, None
            previous.abort()
        params = urlencode(dict(self._filters, offset=offset, limit=PAGE_SIZE))
        reply = self._api.web_request(
            f'/api/operations/{self._resource}?{params}', authenticated=True
        )
        self._reply = reply
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._finish(reply, offset))
        self._status.setText('Loading…')
        self._previous.setEnabled(False)
        self._next.setEnabled(False)

    def _finish(self, reply: QNetworkReply, offset: int) -> None:
        reply.deleteLater()
        if reply is not self._reply:
            return
        self._reply = None
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._status.setText('History lookup failed.')
            return
        try:
            result = json.loads(bytes(reply.readAll()))
            rows = result['rows']
            matching = int(result['matching'])
        except (ValueError, TypeError, KeyError):
            self._status.setText('Invalid history response.')
            return
        self._offset = offset
        self._table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, key in enumerate(FIELDS[self._resource]):
                value = row.get(key)
                item = QTableWidgetItem('—' if value is None else str(value))
                item.setToolTip(item.text())
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(index, column, item)
        self._previous.setEnabled(offset > 0)
        self._next.setEnabled(offset + PAGE_SIZE < matching)
        self._status.setText(f'{matching} matching records · offset {offset}')
