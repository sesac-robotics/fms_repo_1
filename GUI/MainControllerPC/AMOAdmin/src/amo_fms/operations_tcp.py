"""Local TCP and remote TLS transport for the provisional read-only operations snapshot."""

from __future__ import annotations

import json
from base64 import b64decode
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtNetwork import QSslSocket, QTcpSocket

from .models import object_value

MAX_FRAME_BYTES = 1024 * 1024
PREFIX_BYTES = 4
TIMEOUT_MS = 10_000


def snapshot_request(token: str) -> bytes:
    """Encode one authorized GET as a bounded UTF-8 JSON frame."""
    if not token or any(char.isspace() for char in token):
        raise ValueError('Invalid bearer token.')
    message = {
        'method': 'GET',
        'path': '/api/operations',
        'headers': {
            'Accept': ['application/json'],
            'Authorization': [f'Bearer {token}'],
        },
        'body': '',
    }
    payload = json.dumps(message, separators=(',', ':')).encode()
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError('Request too large.')
    return len(payload).to_bytes(PREFIX_BYTES, 'big') + payload


def snapshot_response(frame: bytes) -> tuple[int, dict[str, Any] | None]:
    """Read a complete frame, enforcing the byte limit and JSON response shape."""
    size = int.from_bytes(frame[:PREFIX_BYTES], 'big')
    if not 0 < size <= MAX_FRAME_BYTES or len(frame) != PREFIX_BYTES + size:
        raise ValueError('Invalid frame size.')
    envelope = object_value(json.loads(frame[PREFIX_BYTES:].decode()))
    status = envelope.get('status')
    data = envelope.get('body')
    headers = envelope.get('headers')
    if (
        type(status) is not int
        or not 200 <= status <= 599
        or not isinstance(data, str)
        or not isinstance(headers, dict)
    ):
        raise ValueError('Invalid response envelope.')
    payload = b64decode(data, validate=True)
    return status, object_value(
        json.loads(payload.decode())
    ) if 200 <= status < 300 else None


class OperationsTcpRequest(QObject):
    """Own a single asynchronous snapshot socket and its millisecond deadline."""

    finished = pyqtSignal(int, object)

    def __init__(
        self, port: int, parent: QObject | None = None, *, host: str = '127.0.0.1'
    ) -> None:
        """Use TCP on IPv4 loopback and verified TLS for other hosts."""
        super().__init__(parent)
        self._port = port
        self._host = host
        self._socket: QTcpSocket
        if host == '127.0.0.1':
            self._socket = QTcpSocket(self)
            self._socket.connected.connect(self._send)
        else:
            tls = QSslSocket(self)
            tls.encrypted.connect(self._send)
            self._socket = tls
        self._socket.setReadBufferSize(PREFIX_BYTES + MAX_FRAME_BYTES)
        self._socket.readyRead.connect(self._read)
        self._socket.disconnected.connect(self._disconnected)
        self._socket.errorOccurred.connect(self._disconnected)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._finish)
        self._outgoing = b''
        self._response = bytearray()
        self._closed = False

    def start(self, token: str) -> None:
        """Start a read-only request with an in-memory bearer token."""
        try:
            self._outgoing = snapshot_request(token)
        except ValueError:
            self._finish()
            return
        self._timer.start(TIMEOUT_MS)
        if isinstance(self._socket, QSslSocket):
            self._socket.connectToHostEncrypted(self._host, self._port)
        else:
            self._socket.connectToHost(self._host, self._port)

    def cancel(self) -> None:
        """Release the socket and timer without signaling a cancelled result."""
        self._close()

    def _send(self) -> None:
        outgoing, self._outgoing = self._outgoing, b''
        if self._socket.write(outgoing) != len(outgoing):
            self._finish()

    def _read(self) -> None:
        if self._closed:
            return
        available = self._socket.bytesAvailable()
        if available > PREFIX_BYTES + MAX_FRAME_BYTES - len(self._response):
            self._finish()
            return
        self._response.extend(bytes(self._socket.read(available)))
        if len(self._response) < PREFIX_BYTES:
            return
        size = int.from_bytes(self._response[:PREFIX_BYTES], 'big')
        if not 0 < size <= MAX_FRAME_BYTES:
            self._finish()
            return
        if len(self._response) < PREFIX_BYTES + size:
            return
        try:
            status, payload = snapshot_response(bytes(self._response))
        except (TypeError, ValueError, RecursionError):
            self._finish()
            return
        self._finish(status, payload)

    def _disconnected(self) -> None:
        self._read()
        self._finish()

    def _close(self) -> None:
        self._closed = True
        self._timer.stop()
        self._socket.abort()
        self._outgoing = b''
        self._response.clear()

    def _finish(self, status: int = 0, payload: dict[str, Any] | None = None) -> None:
        if self._closed:
            return
        self._close()
        self.finished.emit(status, payload)
