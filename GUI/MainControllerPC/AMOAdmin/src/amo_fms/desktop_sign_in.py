"""Open the shared admin Web sign-in and correlate its loopback response."""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices

from .desktop_loopback import Loopback


def code_challenge(verifier: str) -> str:
    """Return the base64url S256 challenge without padding."""
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def sign_in_url(origin: str, port: int, verifier: str, state: str) -> str:
    """Build the browser bridge URL without embedding the verifier."""
    query = urlencode(
        {'port': port, 'challenge': code_challenge(verifier), 'state': state}
    )
    return f'{origin}/desktop-sign-in?{query}'


class DesktopSignIn(QObject):
    """Own one pending browser authorization and its local listener."""

    ready = pyqtSignal(int, str, str)
    failed = pyqtSignal(str)

    def __init__(self, origin: str, parent: QObject | None = None) -> None:
        """Use the configured admin Web origin and a bounded loopback wait."""
        super().__init__(parent)
        self._origin = origin
        self._listener = Loopback(self)
        self._listener.completed.connect(self._completed)
        self._deadline = QTimer(self)
        self._deadline.setSingleShot(True)
        self._deadline.timeout.connect(lambda: self._failure('browser_timeout'))
        self._port = 0
        self._verifier = ''

    def start(self, browser_message: str) -> None:
        """Open the system browser and wait up to two minutes for authorization."""
        if self._deadline.isActive():
            return
        state = secrets.token_urlsafe(32)
        self._verifier = secrets.token_urlsafe(48)
        try:
            self._port = self._listener.start(state, browser_message)
        except OSError:
            self._failure('browser_failed')
            return
        self._deadline.start(120_000)
        url = sign_in_url(self._origin, self._port, self._verifier, state)
        if not QDesktopServices.openUrl(QUrl(url)):
            self._failure('browser_failed')

    def cancel(self) -> None:
        """Stop the listener and forget all temporary sign-in material."""
        self._deadline.stop()
        self._listener.close()
        self._verifier = ''
        self._port = 0

    def _completed(self, code: str) -> None:
        if not self._deadline.isActive():
            return
        if not code:
            self._failure('browser_cancelled')
            return
        port, verifier = self._port, self._verifier
        self.cancel()
        self.ready.emit(port, code, verifier)

    def _failure(self, reason: str) -> None:
        self.cancel()
        self.failed.emit(reason)
