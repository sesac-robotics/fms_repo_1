"""Paint a red, yellow and green signal head, shared by the map and the signals page."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

LIT = {'R': '#e5484d', 'Y': '#f5b400', 'G': '#2fbf71'}
OFF = '#3a3f45'
HOUSING = '#1f2328'
ORDER = 'RYG'
WALK = 'RG'  # pedestrian head: no yellow lamp


def paint_head(
    painter: QPainter,
    box: QRectF,
    lit: str,
    *,
    horizontal: bool = False,
    reverse: bool = False,
    lamps: str = ORDER,
    outline: str = '',
) -> None:
    """Draw three lamps inside ``box``; ``lit`` is 'R', 'Y', 'G' or '' for unknown.

    Lamps run red to green top to bottom, or left to right when ``horizontal``;
    ``reverse`` runs them the other way. ``lamps`` is ORDER or WALK; a WALK head
    shows the firmware's flashing pedestrian green (reported as 'Y') as green.
    ``outline``
    draws a highlight border, used for hover on the map.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    radius = min(box.width(), box.height()) * 0.22
    painter.setPen(QPen(QColor(outline), 2.5) if outline else Qt.PenStyle.NoPen)
    painter.setBrush(QColor(HOUSING))
    painter.drawRoundedRect(box, radius, radius)
    painter.setPen(Qt.PenStyle.NoPen)
    long_side = box.width() if horizontal else box.height()
    short_side = box.height() if horizontal else box.width()
    if lit == 'Y' and lit not in lamps:
        lit = 'G'
    cell = long_side / len(lamps)
    lamp = min(cell, short_side) * 0.72
    for index, colour in enumerate(lamps[::-1] if reverse else lamps):
        centre = cell * (index + 0.5)
        x = box.left() + (centre if horizontal else short_side / 2)
        y = box.top() + (short_side / 2 if horizontal else centre)
        painter.setBrush(QColor(LIT[colour] if colour == lit else OFF))
        painter.drawEllipse(QRectF(x - lamp / 2, y - lamp / 2, lamp, lamp))
    painter.restore()


class SignalHead(QWidget):
    """A fixed-size vertical head for the signals page."""

    def __init__(self, lamps: str = ORDER, lamp_px: int = 30) -> None:
        """Start with red lit, matching the firmware's power-on phase."""
        super().__init__()
        self._lit = 'R'
        self._lamps = lamps
        self.setFixedSize(lamp_px + 8, (lamp_px + 4) * len(lamps) + 4)

    def set_lit(self, lamp: str) -> None:
        """Light 'R', 'Y' or 'G'; repaint only on change."""
        if lamp != self._lit:
            self._lit = lamp
            self.update()

    def paintEvent(self, _event: QPaintEvent | None) -> None:
        """Fill the widget with one head."""
        painter = QPainter(self)
        box = QRectF(0, 0, self.width(), self.height())
        paint_head(painter, box, self._lit, lamps=self._lamps)
        painter.end()
