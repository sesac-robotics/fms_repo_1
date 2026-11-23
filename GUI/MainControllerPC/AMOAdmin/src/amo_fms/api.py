"""Read-only operations over provisional IF-03 for the FMS."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from .measurement import observe
from .models import Snapshot
from .operations_tcp import OperationsTcpRequest
from .staff_api import StaffApi


class PreviewApi(StaffApi):
    """Add the read-only fleet connection to a staff Web session."""

    snapshot_received = pyqtSignal(object)

    def __init__(self, endpoint: str, port: int, parent: QObject | None = None) -> None:
        """Use the given Web origin and loopback IF-03 port for this session."""
        super().__init__(endpoint, parent)
        self._port = port
        self._operations: OperationsTcpRequest | None = None

    def refresh(self) -> None:
        """Fetch one read-only IF-03 snapshot without any Web HTTP fallback."""
        if not self._token:
            return
        if self._operations is not None:
            observe('poll_skipped')
            return
        observe('poll_started')
        request = OperationsTcpRequest(self._port, self)
        self._operations = request
        request.finished.connect(
            lambda status, payload: self._finish_refresh(request, status, payload)
        )
        request.start(self._token)

    def _finish_refresh(
        self,
        request: OperationsTcpRequest,
        status: int,
        payload: dict[str, Any] | None,
    ) -> None:
        request.deleteLater()
        if request is not self._operations:
            return
        self._operations = None
        observe('poll_response', status=status)
        if status in {401, 403}:
            self._expire_session()
            return
        if not 200 <= status < 300:
            self.failed.emit('operations', 'snapshot_unavailable')
            return
        try:
            snapshot = Snapshot.parse(payload)
        except (ValueError, TypeError):
            self.failed.emit('operations', 'snapshot_unavailable')
            return
        self.snapshot_received.emit(snapshot)

    def _clear(self) -> None:
        request, self._operations = self._operations, None
        if request is not None:
            request.cancel()
            request.deleteLater()
        super()._clear()
