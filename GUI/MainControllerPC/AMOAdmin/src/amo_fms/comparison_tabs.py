"""Apply shared server menu metadata to the authorized comparison tabs."""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QTabWidget, QWidget

from .staff_api import StaffApi


class ComparisonTabs(QTabWidget):
    """Retain tab widgets while updating labels, order, and visibility."""

    def __init__(
        self, api: StaffApi, role: str, language: str, parent: QWidget
    ) -> None:
        """Use the same menu endpoint as Web for the current staff role."""
        super().__init__(parent)
        self._api = api
        self._path = '/api/admin/menu' if role == 'ADMIN' else '/api/menu'
        self._label = {'ko': 'labelKo', 'en': 'labelEn', 'zh-Hans': 'labelZh'}[language]
        self._keys: list[str] = []

    def add_menu(self, key: str, widget: QWidget, title: str) -> None:
        """Register a tab whose role was already checked by the caller."""
        self._keys.append(key)
        self.addTab(widget, title)
        self.tabBar().setTabData(self.count() - 1, key)

    def load(self) -> None:
        """Load the navigation configuration without blocking Qt polling."""
        reply = self._api.web_request(self._path, authenticated=True)
        self.destroyed.connect(reply.abort)
        reply.finished.connect(lambda: self._received(reply))

    def _received(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                self.apply_rows(json.loads(bytes(reply.readAll())))
            except (ValueError, TypeError, KeyError):
                return

    def apply_rows(self, rows: list[dict[str, Any]]) -> None:
        """Apply display metadata to known tabs, keeping settings accessible."""
        known = {item['key']: item for item in rows if isinstance(item, dict)}
        bar = self.tabBar()
        order = sorted(
            self._keys, key=lambda key: known.get(key, {}).get('position', 999)
        )
        for target, key in enumerate(order):
            index = next(i for i in range(self.count()) if bar.tabData(i) == key)
            bar.moveTab(index, target)
            item = known.get(key, {})
            if label := item.get(self._label):
                self.setTabText(target, label)
            self.setTabVisible(target, key == 'settings' or item.get('visible', True))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
