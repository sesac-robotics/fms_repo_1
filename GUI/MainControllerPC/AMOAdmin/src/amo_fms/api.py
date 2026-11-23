"""Authentication over Web HTTP and read-only operations over provisional IF-03."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from PyQt6.QtCore import QByteArray, QObject, QTimer, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .measurement import observe
from .models import Operator, Snapshot, object_value, string_field
from .operations_tcp import OperationsTcpRequest
from .web_transport import web_request


class PreviewApi(QObject):
    """Coordinate separate authentication and operations connections."""

    authenticated = pyqtSignal(object)
    snapshot_received = pyqtSignal(object)
    failed = pyqtSignal(str, str)
    session_ended = pyqtSignal(str)

    def __init__(self, endpoint: str, port: int, parent: QObject | None = None) -> None:
        """Create Web authentication and loopback IF-03 clients for one session."""
        super().__init__(parent)
        self._endpoint = endpoint
        self._port = port
        self._network = QNetworkAccessManager(self)
        self._token = ''
        self._operations: OperationsTcpRequest | None = None
        self._login_reply: QNetworkReply | None = None
        self._expiration = QTimer(self)
        self._expiration.setSingleShot(True)
        self._expiration.timeout.connect(self._expire_session)

    def web_request(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        *,
        authenticated: bool = False,
        put: bool = False,
    ) -> QNetworkReply:
        """Start a Web GET, JSON POST, or JSON PUT; the caller owns completion and deletion."""
        request = web_request(
            self._endpoint + path, self._token if authenticated else ''
        )
        if data is None:
            return self._network.get(request)
        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json'
        )
        payload = QByteArray(json.dumps(data).encode())
        send = self._network.put if put else self._network.post
        return send(request, payload)

    def login(self, email: str, password: str) -> None:
        """Authenticate directly for protocol integration tests."""
        self._authenticate('/api/auth/login', {'email': email, 'password': password})

    def login_desktop(self, port: int, code: str, verifier: str) -> None:
        """Redeem one browser code using the original loopback port and verifier."""
        self._authenticate(
            '/api/auth/desktop/token',
            {'port': port, 'code': code, 'verifier': verifier},
        )

    def _authenticate(self, path: str, data: dict[str, str | int]) -> None:
        if self._login_reply is not None:
            return
        reply = self.web_request(path, data)
        self._login_reply = reply
        reply.finished.connect(lambda: self._finish_login(reply))

    @staticmethod
    def _status(reply: QNetworkReply) -> int:
        return int(
            reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) or 0
        )

    @staticmethod
    def _payload(reply: QNetworkReply) -> dict[str, Any]:
        if reply.bytesAvailable() > 2_000_000:
            raise ValueError('Response too large.')
        return object_value(json.loads(bytes(reply.readAll())))

    def _finish_login(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply is not self._login_reply:
            return
        self._login_reply = None
        status = self._status(reply)
        if not 200 <= status < 300:
            self.failed.emit(
                'login',
                'login_role'
                if status == 403
                else 'login_invalid'
                if status == 401
                else 'service_error',
            )
            return
        try:
            payload = self._payload(reply)
            operator = Operator.parse(payload.get('user'))
            token = string_field(payload, 'token')
            if not token or any(c.isspace() for c in token):
                raise ValueError('Missing bearer token.')
            deadline = datetime.fromisoformat(string_field(payload, 'expiresAt'))
            if deadline.tzinfo is None:
                raise ValueError('Missing session expiry time zone.')
            remaining = (deadline - datetime.now(UTC)).total_seconds()
            if not 0 < remaining <= 24 * 60 * 60:
                raise ValueError('Invalid session expiry.')
        except PermissionError:
            self.failed.emit('login', 'login_role')
            return
        except (ValueError, TypeError):
            self.failed.emit('login', 'service_error')
            return
        self._token = token
        self._expiration.start(max(1, int(remaining * 1000)))
        self.authenticated.emit(operator)

    def cancel_login(self) -> None:
        """Ignore and abort an unfinished token exchange without ending a session."""
        reply, self._login_reply = self._login_reply, None
        if reply is not None:
            reply.abort()

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
        self._expiration.stop()
        self.cancel_login()
        request, self._operations = self._operations, None
        if request is not None:
            request.cancel()
            request.deleteLater()
        self._token = ''

    def _expire_session(self) -> None:
        self._clear()
        self.session_ended.emit('session_expired')

    def logout(self) -> None:
        """End the local session immediately and request server-side logout."""
        if self._token:
            reply = self.web_request('/api/auth/logout', {}, authenticated=True)
            completed: Callable[[], None] = reply.deleteLater
            reply.finished.connect(completed)
        self._clear()
        self.session_ended.emit('')
