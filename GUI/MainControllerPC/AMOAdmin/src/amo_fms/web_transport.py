"""HTTP request policy shared by desktop Web API calls."""

from time import monotonic_ns

from PyQt6.QtCore import QUrl
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

from .measurement import observe


def web_request(url: str, token: str) -> QNetworkRequest:
    """Build a request with explicit cookie, redirect, and timeout policies."""
    request = QNetworkRequest(QUrl(url))
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
    if token:
        request.setRawHeader(b'Authorization', f'Bearer {token}'.encode())
    return request


def trace_admin_reply(reply: QNetworkReply, path: str) -> QNetworkReply:
    """Record completion timing for a staff read without recording its search."""
    endpoint = path.partition('?')[0]
    if endpoint.startswith(('/api/admin/', '/api/operations/')):
        started = monotonic_ns()

        def finished() -> None:
            observe(
                'admin_response',
                endpoint=endpoint,
                status=reply.attribute(
                    QNetworkRequest.Attribute.HttpStatusCodeAttribute
                ),
                elapsed_ms=(monotonic_ns() - started) / 1_000_000,
            )

        reply.finished.connect(finished)
    return reply
