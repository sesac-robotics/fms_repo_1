"""Fetch a bounded staff overview from the Web gateway on demand."""

from __future__ import annotations

import json

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QNetworkReply

from .models import Snapshot
from .staff_api import StaffApi


class OperationsRead(QObject):
    """Own one asynchronous Web snapshot request and discard canceled results."""

    received = pyqtSignal(object)
    failed = pyqtSignal()

    def __init__(self, api: StaffApi, parent: QObject) -> None:
        """Use the staff session owned by the independent admin window."""
        super().__init__(parent)
        self._api = api
        self._reply: QNetworkReply | None = None

    def load(self) -> bool:
        """Start a request when idle and report whether it was started."""
        if self._reply is not None:
            return False
        reply = self._api.web_request('/api/operations', authenticated=True)
        self._reply = reply
        reply.finished.connect(lambda: self._finish(reply))
        return True

    def cancel(self) -> None:
        """Abort the current request without delivering its response."""
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.abort()

    def _finish(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply is not self._reply:
            return
        self._reply = None
        if (
            reply.error() != QNetworkReply.NetworkError.NoError
            or reply.bytesAvailable() > 2_000_000
        ):
            self.failed.emit()
            return
        try:
            snapshot = Snapshot.parse(json.loads(bytes(reply.readAll())))
        except (TypeError, ValueError):
            self.failed.emit()
            return
        self.received.emit(snapshot)
