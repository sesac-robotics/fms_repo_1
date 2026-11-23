"""Display a recorded trip route in the shared v0.2 map frame."""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QPixmap
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .api import PreviewApi
from .map_preview import map_fraction


def segments(payload: dict[str, Any]) -> list[list[tuple[float, float]]]:
    """Convert bounded metric samples to image fractions, retaining segment breaks."""
    if payload.get('mapVersion') != 'v0.2' or payload.get('frameId') != 'schematic_v02':
        return []
    lines = []
    for segment in payload['segments']:
        points = [map_fraction((float(p['xM']), float(p['yM']))) for p in segment]
        if len(points) >= 2 and all(p is not None for p in points):
            lines.append([p for p in points if p is not None])
    return lines


class RouteDialog(QDialog):
    """Read a selected request route asynchronously and show stored positions."""

    def __init__(
        self, api: PreviewApi, request_id: int, asset: str, parent: QWidget
    ) -> None:
        """Open an independent route view with a stable request ID."""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(f'Recorded route #{request_id}')
        self.resize(750, 600)
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._map = QPixmap(asset)
        self._scene.addPixmap(self._map)
        self._status = QLabel('Loading recorded route…')
        layout = QVBoxLayout(self)
        layout.addWidget(self._status)
        layout.addWidget(self._view)
        request = api.web_request(
            f'/api/operations/requests/{request_id}/route', authenticated=True
        )
        self.destroyed.connect(request.abort)
        request.finished.connect(lambda: self._complete(request))

    def _complete(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._status.setText('Recorded route lookup failed.')
            return
        try:
            payload = json.loads(bytes(reply.readAll()))
            lines = segments(payload)
        except (ValueError, TypeError, KeyError, AttributeError):
            self._status.setText('Invalid route response.')
            return
        if not lines:
            self._status.setText('No recorded route.')
            return
        width, height = self._map.width(), self._map.height()
        if self._map.isNull():
            self._status.setText('Map unavailable.')
            return
        for first, *points in lines:
            path = QPainterPath()
            path.moveTo(first[0] * width, first[1] * height)
            for x, y in points:
                path.lineTo(x * width, y * height)
            self._scene.addPath(path, QPen(QColor('#E34F2F'), 5))
        self._view.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )
        self._status.setText(
            'Partial recorded route.' if payload.get('truncated') else 'Recorded route.'
        )
