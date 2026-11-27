"""Draw intersection signals on the confirmed map and open the signals page on click."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen

from .confirmed_review_map import ConfirmedReviewMap
from .review_lanes import BOARD
from .signal_head import ORDER, WALK, paint_head
from .signal_layout import INTERSECTIONS, Intersection, Mast
from .signal_readings import SignalReading

_HEAD_PX = (40.0, 16.0)  # long side, short side of a head; fixed on screen
_BORDER = '#ffffff'  # separates the signal from the dark road artwork
_HOVER = '#4cc9f0'
_POLE = '#6b7079'
_POLE_RADIUS = 5.0


class SignalMap(ConfirmedReviewMap):
    """Confirmed map that also shows live signal lamps and reports intersection clicks."""

    def __init__(
        self,
        source: Path,
        description: str,
        unavailable: str,
        open_signal: Callable[[str], None],
    ) -> None:
        """Call ``open_signal(signal_id)`` when an intersection is clicked."""
        super().__init__(source, description, unavailable)
        self._open = open_signal
        self._readings: dict[str, SignalReading] = {}
        self._hovered: tuple[str, ...] = ()
        self.setMouseTracking(True)

    def show_signals(self, readings: tuple[SignalReading, ...]) -> None:
        """Repaint with the latest lamps; unknown signals are drawn unlit."""
        self._readings = {reading.signal_id: reading for reading in readings}
        self.update()

    def hit(self, point: QPointF) -> str:
        """Return the first signal ID under a widget point, or ''."""
        return next(iter(self._hits(point)), '')

    def _hits(self, point: QPointF) -> tuple[str, ...]:
        """Every signal whose heads or intersection area contain the point."""
        return tuple(
            crossing.signal_id
            for crossing in INTERSECTIONS
            if any(
                box is not None and box.contains(point)
                for box in (*self._heads(crossing), self._area(crossing))
            )
        )

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        """Show a pointer and highlight every head of the hovered intersection."""
        hovered = self._hits(event.position()) if event else ()
        if hovered != self._hovered:
            self._hovered = hovered
            self.setCursor(
                Qt.CursorShape.PointingHandCursor
                if hovered
                else Qt.CursorShape.ArrowCursor
            )
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Open the signals page for a clicked intersection."""
        signal_id = self.hit(event.position()) if event else ''
        if signal_id and event.button() == Qt.MouseButton.LeftButton:
            self._open(signal_id)
            return
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Paint the review marker first, then the signal heads on top."""
        super().paintEvent(event)
        painter = QPainter(self)
        for crossing in INTERSECTIONS:
            boxes = self._heads(crossing)
            if boxes[0] is None or boxes[1] is None:
                continue
            reading = self._readings.get(crossing.signal_id)
            lamps = reading.lamps() if reading else ('', '')
            outline = _HOVER if crossing.signal_id in self._hovered else _BORDER
            for mast, box, lamp in zip(
                (crossing.a, crossing.b), boxes, lamps, strict=True
            ):
                self._paint_mast(painter, mast)
                paint_head(
                    painter,
                    box,
                    lamp,
                    horizontal=mast.horizontal,
                    reverse=mast.reverse,
                    lamps=WALK if mast.pedestrian else ORDER,
                    outline=outline,
                )
        painter.end()

    def _paint_mast(self, painter: QPainter, mast: Mast) -> None:
        pole = self._to_widget(*mast.pole)
        head = self._to_widget(*mast.head)
        if pole is None or head is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # A white casing under the grey arm keeps it visible on the dark road.
        for colour, width in ((_BORDER, 5.0), (_POLE, 3.0)):
            painter.setPen(QPen(QColor(colour), width, cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(pole, head)
        painter.setPen(QPen(QColor(_BORDER), 2.0))
        painter.setBrush(QColor(_POLE))
        painter.drawEllipse(pole, _POLE_RADIUS, _POLE_RADIUS)
        painter.restore()

    def _to_widget(self, x: float, y: float) -> QPointF | None:
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return None
        size = pixmap.deviceIndependentSize()
        return QPointF(
            (self.width() - size.width()) / 2 + x * size.width() / BOARD[0],
            (self.height() - size.height()) / 2 + y * size.height() / BOARD[1],
        )

    def _heads(self, crossing: Intersection) -> tuple[QRectF | None, QRectF | None]:
        a_box, b_box = (self._head_box(mast) for mast in (crossing.a, crossing.b))
        return a_box, b_box

    def _head_box(self, mast: Mast) -> QRectF | None:
        centre = self._to_widget(*mast.head)
        if centre is None:
            return None
        long, short = _HEAD_PX
        if mast.pedestrian:
            long = long * len(WALK) / len(ORDER)
        width, height = (long, short) if mast.horizontal else (short, long)
        return QRectF(centre.x() - width / 2, centre.y() - height / 2, width, height)

    def _area(self, crossing: Intersection) -> QRectF | None:
        left, top, right, bottom = crossing.area
        start = self._to_widget(left, top)
        end = self._to_widget(right, bottom)
        return QRectF(start, end) if start and end else None
