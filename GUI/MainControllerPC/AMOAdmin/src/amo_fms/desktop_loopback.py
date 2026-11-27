"""Local-only HTTP callback boundary for desktop sign-in."""

from __future__ import annotations

import re
import secrets
from urllib.parse import parse_qs, urlsplit

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

CALLBACK_PATH = '/amo-callback'
CODE_FORMAT = re.compile(r'[A-Za-z0-9_-]{43}')


def callback_code(target: str, expected_state: str) -> str:
    """Return a broker code or explicit denial from one matching relative callback."""
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or parts.fragment or parts.path != CALLBACK_PATH:
        raise ValueError('Invalid callback path.')
    query = parse_qs(parts.query, keep_blank_values=True, max_num_fields=8)
    states = query.get('state', [])
    if (
        len(states) != 1
        or not states[0].isascii()
        or not secrets.compare_digest(states[0], expected_state)
    ):
        raise ValueError('Invalid callback state.')
    if query.get('error') == ['access_denied'] and 'code' not in query:
        return ''
    codes = query.get('code', [])
    if 'error' in query or len(codes) != 1 or not CODE_FORMAT.fullmatch(codes[0]):
        raise ValueError('Missing authorization code.')
    return codes[0]


class Loopback(QObject):
    """Receive one correlated callback on an ephemeral IPv4 loopback port."""

    completed = pyqtSignal(str)

    def __init__(self, parent: QObject) -> None:
        """Create a listener with no public network binding."""
        super().__init__(parent)
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._accept)
        self._server.setMaxPendingConnections(4)
        self._state = ''
        self._message = ''
        self._sockets: set[QTcpSocket] = set()

    def start(self, state: str, message: str) -> int:
        """Bind IPv4 loopback and return the randomly assigned TCP port."""
        self.close()
        self._state = state
        self._message = message
        if not self._server.listen(QHostAddress.SpecialAddress.LocalHost, 0):
            raise OSError('Could not start the desktop loopback callback.')
        return self._server.serverPort()

    def close(self) -> None:
        """Stop accepting callbacks and abort unfinished sockets."""
        self._server.close()
        self._state = ''
        self._message = ''
        for socket in tuple(self._sockets):
            socket.abort()
            socket.deleteLater()
        self._sockets.clear()

    def _accept(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                return
            if len(self._sockets) >= 4:
                socket.abort()
                socket.deleteLater()
                continue
            self._sockets.add(socket)
            socket.setReadBufferSize(8193)
            socket.readyRead.connect(lambda sock=socket: self._read(sock))
            socket.disconnected.connect(lambda sock=socket: self._forget(sock))
            self._read(socket)

    def _forget(self, socket: QTcpSocket) -> None:
        self._sockets.discard(socket)
        socket.deleteLater()

    def _reply(self, socket: QTcpSocket, status: str, message: str) -> None:
        content = message.encode('utf-8')
        header = (
            f'HTTP/1.1 {status}\r\nContent-Type: text/plain; charset=utf-8\r\n'
            f'Cache-Control: no-store\r\nReferrer-Policy: no-referrer\r\n'
            f'Connection: close\r\n'
            f'Content-Length: {len(content)}\r\n\r\n'
        ).encode()
        socket.write(header + content)
        socket.disconnectFromHost()

    def _read(self, socket: QTcpSocket) -> None:
        data = bytes(socket.peek(socket.bytesAvailable()))
        if len(data) > 8192:
            self._reply(socket, '400 Bad Request', 'Invalid callback.')
            return
        if b'\r\n\r\n' not in data:
            return
        socket.readAll()
        try:
            headers = data.split(b'\r\n\r\n', 1)[0].split(b'\r\n')
            method, target, protocol = headers[0].decode('ascii').split(' ')
            hosts = [
                line.partition(b':')[2].strip()
                for line in headers[1:]
                if line.partition(b':')[0].lower() == b'host'
            ]
            expected_host = f'127.0.0.1:{self._server.serverPort()}'.encode()
            if (
                method != 'GET'
                or protocol != 'HTTP/1.1'
                or not self._state
                or hosts != [expected_host]
            ):
                raise ValueError('Unexpected method.')
            code = callback_code(target, self._state)
        except (ValueError, UnicodeError):
            self._reply(socket, '400 Bad Request', 'Invalid callback.')
            return
        self._state = ''
        self._server.close()
        socket.disconnected.connect(lambda: self.completed.emit(code))
        self._reply(socket, '200 OK', self._message)
