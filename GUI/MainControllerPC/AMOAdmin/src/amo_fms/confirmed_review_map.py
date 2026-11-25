"""Draw a synthetic marker and animate committed paths on the confirmed map."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from time import monotonic

from PyQt6.QtCore import QPointF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen

from .review_lanes import BOARD, DEPOT, along, movements
from .review_lanes import Path as LanePath
from .review_playback import Playback
from .widgets import FitImage

_SECONDS = 1.35


class ConfirmedReviewMap(FitImage):
    """Show one current review, discarding queued movement when its run changes."""

    def __init__(self, source: Path, description: str, unavailable: str) -> None:
        """Load the shared map and allocate the animation timer."""
        super().__init__(source, description, unavailable)
        self._review: Playback | None = None
        self._point = DEPOT
        self._pending: deque[LanePath] = deque()
        self._started = 0.0
        self._clock = QTimer(self)
        self._clock.setInterval(25)
        self._clock.timeout.connect(self._tick)

    def present(self, review: Playback | None) -> None:
        """Apply a consistent server snapshot, keeping playback separate from vehicle telemetry."""
        previous, self._review = self._review, review
        if review is None:
            self._reset_animation()
            self.update()
            return
        paths = movements(review.checkpoints)
        if previous is None or previous.run_id != review.run_id:
            self._reset_animation()
            self._point = paths[-1][-1] if paths else DEPOT
        else:
            offset = len(previous.checkpoints)
            for checkpoint, path in zip(
                review.checkpoints[offset:], paths[offset:], strict=True
            ):
                if checkpoint.step == 'LINK_LOST':
                    self._reset_animation()
                    self._point = path[-1]
                elif len(path) > 1:
                    self._pending.append(path)
            if self._pending and not self._clock.isActive():
                self._started = monotonic()
                self._clock.start()
        self.update()

    def _reset_animation(self) -> None:
        self._clock.stop()
        self._pending.clear()
        self._point = DEPOT

    def _tick(self) -> None:
        progress = (monotonic() - self._started) / _SECONDS
        self._point = along(self._pending[0], progress)
        if progress >= 1:
            self._pending.popleft()
            self._started = monotonic()
            if not self._pending:
                self._clock.stop()
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Paint the marker relative to the actual letterboxed image."""
        super().paintEvent(event)
        if self._review is None:
            return
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return
        width = pixmap.deviceIndependentSize().width()
        height = pixmap.deviceIndependentSize().height()
        x, y = self._point
        point = QPointF(
            (self.width() - width) / 2 + x * width / BOARD[0],
            (self.height() - height) / 2 + y * height / BOARD[1],
        )
        last = self._review.checkpoints[-1] if self._review.checkpoints else None
        stopped = last and last.step in {
            'LINK_LOST',
            'LINK_RESTORED',
            'PREPAY_DECLINED',
        }
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#a94712' if stopped else '#036e60'))
        painter.setPen(QPen(QColor('#ffffff'), 2.5))
        painter.drawEllipse(point, 10, 10)
        painter.end()
