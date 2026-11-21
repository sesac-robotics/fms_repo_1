"""Asynchronous REST demo adapter. It never sends vehicle control requests."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from PyQt6.QtCore import QByteArray, QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .models import Operator, Snapshot, object_value, string_field


class PreviewApi(QObject):
    """Use the development backend while keeping bearer tokens in process memory."""

    authenticated = pyqtSignal(object)
    snapshot_received = pyqtSignal(object)
    failed = pyqtSignal(str, str)
    session_ended = pyqtSignal(str)

    def __init__(self, endpoint: str, parent: QObject | None = None) -> None:
        """Create one background network manager for the configured backend origin."""
        super().__init__(parent)
        self._endpoint = endpoint
        self._network = QNetworkAccessManager(self)
        self._token = ''
        self._generation = 0
        self._loading = False
        self._login_reply: QNetworkReply | None = None
        self._expiration = QTimer(self)
        self._expiration.setSingleShot(True)
        self._expiration.timeout.connect(self._expire_session)

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> QNetworkReply:
        request = QNetworkRequest(QUrl(f'{self._endpoint}{path}'))
        request.setTransferTimeout(10_000)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.ManualRedirectPolicy,
        )
        request.setAttribute(
            QNetworkRequest.Attribute.CookieLoadControlAttribute,
            QNetworkRequest.LoadControl.Manual,
        )
        request.setAttribute(
            QNetworkRequest.Attribute.CookieSaveControlAttribute,
            QNetworkRequest.LoadControl.Manual,
        )
        request.setRawHeader(b'Accept', b'application/json')
        if authenticated and self._token:
            request.setRawHeader(b'Authorization', f'Bearer {self._token}'.encode())
        if method == 'GET':
            return self._network.get(request)
        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json'
        )
        return self._network.post(request, QByteArray(json.dumps(data).encode()))

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
        reply = self._request('POST', path, data)
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
        """Fetch a single server snapshot and never replay a command."""
        if not self._token or self._loading:
            return
        self._loading = True
        generation = self._generation
        reply = self._request('GET', '/api/operations', authenticated=True)
        reply.finished.connect(lambda: self._finish_refresh(reply, generation))

    def _finish_refresh(self, reply: QNetworkReply, generation: int) -> None:
        reply.deleteLater()
        if generation != self._generation:
            return
        self._loading = False
        status = self._status(reply)
        if status in {401, 403}:
            self._expire_session()
            return
        if not 200 <= status < 300:
            self.failed.emit('operations', 'snapshot_unavailable')
            return
        try:
            snapshot = Snapshot.parse(self._payload(reply))
        except (ValueError, TypeError):
            self.failed.emit('operations', 'snapshot_unavailable')
            return
        self.snapshot_received.emit(snapshot)

    def _clear(self) -> None:
        self._expiration.stop()
        self._generation += 1
        self.cancel_login()
        self._loading = False
        self._token = ''

    def _expire_session(self) -> None:
        self._clear()
        self.session_ended.emit('session_expired')

    def logout(self) -> None:
        """End the local session immediately and request server-side logout."""
        if self._token:
            reply = self._request('POST', '/api/auth/logout', {}, authenticated=True)
            completed: Callable[[], None] = reply.deleteLater
            reply.finished.connect(completed)
        self._clear()
        self.session_ended.emit('')
