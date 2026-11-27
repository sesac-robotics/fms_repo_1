"""Edit existing Web menu metadata through authorized Main Control APIs."""

from __future__ import annotations

import json
from urllib.parse import quote

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from .staff_api import StaffApi


class MenuPanel(QWidget):
    """List and edit labels, display order, and visibility for one menu at a time."""

    changed = pyqtSignal()

    def __init__(self, api: StaffApi, parent: QWidget) -> None:
        """Use the current bearer session for bounded menu requests."""
        super().__init__(parent)
        self._api = api
        self._rows: list[dict] = []
        self._pending = False
        layout = QFormLayout(self)
        self._items = QComboBox()
        self._items.currentIndexChanged.connect(self._select)
        layout.addRow('Menu', self._items)
        self._labels: dict[str, QLineEdit] = {}
        for key, label in (
            ('labelKo', '한국어'),
            ('labelEn', 'English'),
            ('labelZh', '简体中文'),
        ):
            field = QLineEdit()
            field.setMaxLength(80)
            self._labels[key] = field
            layout.addRow(label, field)
        self._position = QSpinBox()
        self._position.setRange(0, 999)
        layout.addRow('Order', self._position)
        self._visible = QCheckBox('Visible')
        layout.addRow(self._visible)
        refresh = QPushButton('Load menus')
        refresh.clicked.connect(self.load)
        layout.addRow(refresh)
        save = QPushButton('Save')
        save.clicked.connect(self._save)
        layout.addRow(save)
        self._status = QLabel()
        layout.addRow(self._status)

    def load(self) -> None:
        """Read all current menu definitions via the admin-only API."""
        if not self._pending:
            self._send('/api/admin/menu')

    def _send(self, path: str, body: dict | None = None) -> None:
        self._pending = True
        reply = self._api.web_request(
            path, body, authenticated=True, put=body is not None
        )
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._complete(reply, body is not None))

    def _complete(self, reply: QNetworkReply, saved: bool) -> None:
        reply.deleteLater()
        self._pending = False
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._status.setText('Menu request failed.')
            return
        if saved:
            self._status.setText('Saved.')
            self.changed.emit()
            self.load()
            return
        try:
            self._rows = json.loads(bytes(reply.readAll()))
            keys = [row['key'] for row in self._rows]
        except (ValueError, TypeError, KeyError):
            self._status.setText('Invalid menu response.')
            return
        self._items.clear()
        self._items.addItems(keys)

    def _select(self, index: int) -> None:
        if not 0 <= index < len(self._rows):
            return
        row = self._rows[index]
        for key, widget in self._labels.items():
            widget.setText(row[key])
        self._position.setValue(row['position'])
        self._visible.setChecked(row['visible'])
        self._visible.setEnabled(row['key'] != 'settings')

    def _save(self) -> None:
        index = self._items.currentIndex()
        if self._pending or index < 0:
            return
        key = self._rows[index]['key']
        body = {field: widget.text().strip() for field, widget in self._labels.items()}
        if not all(body.values()):
            self._status.setText('All three labels are required.')
            return
        self._send(
            '/api/admin/menu/' + quote(key, safe=''),
            dict(
                body,
                key=key,
                position=self._position.value(),
                visible=self._visible.isChecked(),
            ),
        )
