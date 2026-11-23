"""HTTP request policy shared by desktop Web API calls."""

from PyQt6.QtCore import QUrl
from PyQt6.QtNetwork import QNetworkRequest


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
