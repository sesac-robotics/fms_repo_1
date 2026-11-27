"""Bounded member searches through the shared gateway."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .staff_api import StaffApi

PAGE_SIZE = 50


class MembersPanel(QWidget):
    """Show a single page of member summaries beside the fleet monitor."""

    def __init__(self, api: StaffApi, parent: QWidget) -> None:
        """Use the signed-in FMS session for cancellable asynchronous requests."""
        super().__init__(parent)
        self._api = api
        self._reply: QNetworkReply | None = None
        self._offset = 0
        self._query: dict[str, str] = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Members and roles'))
        self._search = QLineEdit()
        self._search.setPlaceholderText('Search name or email')
        self._search.setMaxLength(100)
        self._search.returnPressed.connect(self._start)
        layout.addWidget(self._search)
        self._newest = QCheckBox('Descending ID')
        layout.addWidget(self._newest)
        controls = QHBoxLayout()
        search = QPushButton('Search')
        search.clicked.connect(self._start)
        controls.addWidget(search)
        self._previous = QPushButton('Previous')
        self._previous.clicked.connect(lambda: self._load(self._offset - PAGE_SIZE))
        self._next = QPushButton('Next')
        self._next.clicked.connect(lambda: self._load(self._offset + PAGE_SIZE))
        for button in (self._previous, self._next):
            button.setEnabled(False)
            controls.addWidget(button)
        layout.addLayout(controls)
        self._status = QLabel()
        layout.addWidget(self._status)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(['Name', 'Email', 'Role', 'Status'])
        self._rows: list[dict[str, str]] = []
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)
        approval = QHBoxLayout()
        self._role = QComboBox()
        self._role.addItems(['OPERATOR', 'ADMIN'])
        approval.addWidget(self._role)
        for label, approved in (('Approve', True), ('Reject', False)):
            button = QPushButton(label)
            button.clicked.connect(lambda _, value=approved: self._review(value))
            approval.addWidget(button)
        add_operator = QPushButton('Add Google operator')
        add_operator.clicked.connect(self._add_operator)
        approval.addWidget(add_operator)
        layout.addLayout(approval)

    def _cancel(self) -> None:
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.abort()

    def _start(self) -> None:
        self._query = {
            'q': self._search.text().strip(),
            'newest': str(self._newest.isChecked()).lower(),
        }
        self._load(0)

    def _load(self, offset: int) -> None:
        self._cancel()
        self._status.setText('Loading…')
        self._previous.setEnabled(False)
        self._next.setEnabled(False)
        query = urlencode(dict(self._query, offset=offset, limit=PAGE_SIZE))
        reply = self._api.web_request(
            f'/api/admin/members/page?{query}', authenticated=True
        )
        self._reply = reply
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._finish(reply, offset))

    def _finish(self, reply: QNetworkReply, offset: int) -> None:
        reply.deleteLater()
        if reply is not self._reply:
            return
        self._reply = None
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._status.setText('Member lookup failed.')
            return
        try:
            page = json.loads(bytes(reply.readAll()))
            self._rows = page['items']
            rows = [
                tuple(item[key] for key in ('name', 'email', 'role', 'status'))
                for item in page['items']
            ]
            has_more = page['hasMore']
        except (ValueError, TypeError, KeyError):
            self._status.setText('Invalid member page.')
            return
        self._offset = offset
        self._table.setRowCount(len(rows))
        for index, values in enumerate(rows):
            for column, value in enumerate(values):
                self._table.setItem(index, column, QTableWidgetItem(str(value)))
        self._previous.setEnabled(offset > 0)
        self._next.setEnabled(bool(has_more))
        self._status.setText(f'{len(rows)} records · offset {offset}')

    def _review(self, approved: bool) -> None:
        if self._reply is not None:
            return
        index = self._table.currentRow()
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        if row['status'] != 'PENDING' or row['role'] == 'PASSENGER':
            self._status.setText('Select a pending staff account.')
            return
        action = 'Approve' if approved else 'Reject'
        if QMessageBox.question(self, action, f'{action} {row["email"]}?') != (
            QMessageBox.StandardButton.Yes
        ):
            return
        body: dict[str, str | bool] = {'approved': approved}
        if approved:
            body['role'] = self._role.currentText()
        self._update_member(int(row['id']), 'approval', body)

    def _add_operator(self) -> None:
        if self._reply is not None:
            return
        index = self._table.currentRow()
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        if row['status'] != 'ACTIVE' or row['role'] != 'PASSENGER':
            self._status.setText('Select an active Google-linked passenger.')
            return
        if (
            QMessageBox.question(
                self, 'Add Google operator', f'Add operator access for {row["email"]}?'
            )
            == QMessageBox.StandardButton.Yes
        ):
            self._update_member(int(row['id']), 'google-operator', {})

    def _update_member(
        self, member_id: int, action: str, body: dict[str, str | bool]
    ) -> None:
        reply = self._api.web_request(
            f'/api/admin/members/{member_id}/{action}',
            body,
            authenticated=True,
            put=True,
        )
        self._reply = reply
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._reviewed(reply))

    def _reviewed(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply is not self._reply:
            return
        self._reply = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self._load(self._offset)
        else:
            self._status.setText('Staff approval request failed.')
