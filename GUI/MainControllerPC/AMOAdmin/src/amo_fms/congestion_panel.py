"""Present a held-out congestion replay on the confirmed drawing in FMS."""

from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import (
    QHeaderView,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .congestion_trace import Trace
from .i18n import Text
from .widgets import FitImage, label


class _IntersectionMap(FitImage):
    def __init__(self, path: Path, tr: Text, anchor: tuple[float, float]) -> None:
        super().__init__(path, tr('forecast_title'), tr('map_missing'))
        self._anchor = anchor

    def paintEvent(self, event: QPaintEvent | None) -> None:
        super().paintEvent(event)
        texture = self.pixmap()
        if texture is None or texture.isNull():
            return
        width, height = (
            texture.deviceIndependentSize().width(),
            texture.deviceIndependentSize().height(),
        )
        center = QPointF(
            (self.width() - width) / 2 + width * self._anchor[0],
            (self.height() - height) / 2 + height * self._anchor[1],
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#ffffff'), 2))
        painter.setBrush(QColor('#036e60'))
        painter.drawEllipse(center, 9, 9)
        painter.end()


class CongestionPanel(QWidget):
    """Expose an optional read-only page with a cursor for simulated observations."""

    def __init__(self, tr: Text, source: Path, map_path: Path) -> None:
        """Load and display one matching experiment or a localized file error."""
        super().__init__()
        self._tr = tr
        layout = QVBoxLayout(self)
        layout.addWidget(label(tr('forecast_scope'), 'secondary'))
        try:
            trace = Trace.read(source, map_path)
        except (OSError, ValueError):
            layout.addWidget(label(tr('forecast_unavailable'), 'warning'))
            layout.addStretch()
            return
        self._trace = trace
        layout.addWidget(_IntersectionMap(map_path, tr, trace.anchor), 1)
        self._time = label('', 'heading')
        layout.addWidget(self._time)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setAccessibleName(tr('forecast_cursor'))
        self._slider.setRange(0, len(trace.frames) - 1)
        layout.addWidget(self._slider)
        self._table = QTableWidget(0, 4)
        self._table.setAccessibleName(tr('forecast_title'))
        self._table.setHorizontalHeaderLabels(
            [
                tr('forecast_horizon'),
                tr('forecast_model'),
                tr('forecast_baseline'),
                tr('forecast_observed'),
            ]
        )
        horizontal = self._table.horizontalHeader()
        if horizontal is not None:
            horizontal.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vertical = self._table.verticalHeader()
        if vertical is not None:
            vertical.hide()
        self._table.setMinimumHeight(110)
        self._table.setMaximumHeight(140)
        layout.addWidget(self._table)
        self._slider.valueChanged.connect(self._present)
        self._present(0)

    def _present(self, index: int) -> None:
        tick, values = self._trace.frames[index]
        self._time.setText(self._tr('forecast_elapsed', seconds=f'{tick / 10:.1f}'))
        self._table.setRowCount(len(values))
        for row, record in enumerate(values):
            self._table.setItem(
                row,
                0,
                QTableWidgetItem(
                    self._tr('forecast_seconds', seconds=record.horizon_s)
                ),
            )
            for column, outcome in enumerate(
                (record.model, record.baseline, record.observed), start=1
            ):
                shown = self._tr(
                    'forecast_value',
                    queue=f'{outcome.queue:.1f}',
                    wait=f'{outcome.wait_s:.1f}',
                )
                self._table.setItem(row, column, QTableWidgetItem(shown))
