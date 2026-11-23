"""Read-only display of points in the v0.2 development map."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QRegion

from .measurement import observe
from .models import Vehicle
from .widgets import FitImage

WIDTH_M = 2.440
HEIGHT_M = 2.225
LABEL_CENTERS = ((260, 563), (829, 563), (280, 774), (894, 848))
VIEWBOX = (1046, 958)


def map_fraction(position_m: tuple[float, float]) -> tuple[float, float] | None:
    """Convert a v0.2 bottom-left-origin metric point to a top-left fraction."""
    x, y = position_m
    if 0.0 <= x <= WIDTH_M and 0.0 <= y <= HEIGHT_M:
        return x / WIDTH_M, 1.0 - y / HEIGHT_M
    return None


def _label_areas(board: QRectF) -> tuple[QRectF, ...]:
    x_scale = board.width() / VIEWBOX[0]
    y_scale = board.height() / VIEWBOX[1]
    return tuple(
        QRectF(
            board.x() + (x - 25) * x_scale,
            board.y() + (y - 20) * y_scale,
            50 * x_scale,
            40 * y_scale,
        )
        for x, y in LABEL_CENTERS
    )


def _badge_bounds(
    anchor: QPointF, radius: float, room: QRectF, occupied: list[QRectF]
) -> QRectF | None:
    gap = radius + 15
    x, y = anchor.x(), anchor.y()
    for cx, cy in ((x, y - gap), (x, y + gap), (x - gap, y), (x + gap, y)):
        bounds = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        edge = bounds.adjusted(-2, -2, 2, 2)
        if room.contains(edge) and not any(edge.intersects(box) for box in occupied):
            return bounds
    return None


class MapPreview(FitImage):
    """Plot only explicit demo data whose frame is the shared v0.2 map."""

    _vehicles: tuple[Vehicle, ...] = ()
    _selected: str = ''
    _painted: tuple[tuple[str, tuple[str, int, str]], ...] = ()

    def show_samples(self, vehicles: tuple[Vehicle, ...], selected: str) -> None:
        """Replace plotted vehicles and update the highlighted sample."""
        self._vehicles = vehicles
        self._selected = selected
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Anchor an outlined callout to each validated map point."""
        super().paintEvent(event)
        texture = self.pixmap()
        if texture is None or texture.isNull() or not self._vehicles:
            return
        width, height = (
            texture.deviceIndependentSize().width(),
            texture.deviceIndependentSize().height(),
        )
        left, top = (self.width() - width) / 2, (self.height() - height) / 2
        board = QRectF(left, top, width, height)
        labels = _label_areas(board)
        used = list(labels)
        drawable = QRegion(board.toAlignedRect())
        for area in labels:
            drawable -= QRegion(area.toAlignedRect())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRegion(drawable)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        samples = []
        for vehicle in self._vehicles:
            if vehicle.position_m is None:
                continue
            point = map_fraction(vehicle.position_m)
            if point is None:
                continue
            x, y = left + width * point[0], top + height * point[1]
            badge = vehicle.number.rsplit('-', 1)[-1]
            radius = max(13, (painter.fontMetrics().horizontalAdvance(badge) + 8) / 2)
            anchor = QPointF(x, y)
            bounds = _badge_bounds(anchor, radius, board, used)
            painter.setBrush(QColor('#31213E' if vehicle.can_preview else '#683800'))
            painter.setPen(
                QPen(
                    QColor('#7FE2BB' if vehicle.id == self._selected else '#FFF0F7'), 3
                )
            )
            painter.drawEllipse(anchor, 3, 3)
            if vehicle.sample is not None:
                samples.append((vehicle.id, vehicle.sample))
            if bounds is None:
                continue
            used.append(bounds)
            painter.drawLine(anchor, bounds.center())
            painter.drawEllipse(bounds)
            painter.setPen(QColor('#FFF0F7'))
            painter.drawText(
                bounds,
                int(Qt.AlignmentFlag.AlignCenter),
                badge,
            )
        painter.end()
        if tuple(samples) != self._painted:
            self._painted = tuple(samples)
            observe('map_painted', samples=samples)
