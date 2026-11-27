"""Send staff signal commands through the Web gateway (IF-02).

The FMS reads snapshots over the read-only IF-03 link. Commands therefore use
the staff Web session that the FMS already holds, the same path the Admin app
uses: POST /api/signals/{signalId}/commands with {"command": "..."}.
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QNetworkRequest

from .staff_api import StaffApi

# HTTP status from Main Control -> translation key shown to the operator.
_RESULTS = {
    202: 'signal_queued',
    400: 'signal_rejected_command',
    401: 'signal_denied',
    403: 'signal_denied',
    404: 'signal_unknown',
}


def result_key(status: int) -> str:
    """Map a gateway status to the message key; anything else is a failure."""
    return _RESULTS.get(status, 'signal_send_failed')


class SignalCommandSender(QObject):
    """Queue one command for a signal and report the outcome to a callback."""

    def __init__(self, api: StaffApi, parent: QObject | None = None) -> None:
        """Use the FMS's existing staff session."""
        super().__init__(parent)
        self._api = api

    def send(self, signal_id: str, command: str, done: Callable[[str], None]) -> None:
        """POST the command; ``done`` receives a translation key when it finishes."""
        reply = self._api.web_request(
            f'/api/signals/{signal_id}/commands',
            {'command': command},
            authenticated=True,
        )

        def finished() -> None:
            # HTTP errors still carry a status; a transport failure has none.
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            done('signal_send_failed' if status is None else result_key(int(status)))
            reply.deleteLater()

        reply.finished.connect(finished)
