"""Give the map and the camera column independently adjustable space."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QSplitter, QWidget

from .i18n import Text
from .widgets import label


def map_and_cameras(road_map: QWidget, sidebar: QWidget) -> QSplitter:
    """Start with a wide camera column and keep the map visible when resized."""
    split = QSplitter(Qt.Orientation.Horizontal)
    split.setChildrenCollapsible(False)
    split.setHandleWidth(10)
    split.addWidget(road_map)
    split.addWidget(sidebar)
    split.setStretchFactor(0, 1)
    split.setStretchFactor(1, 1)
    split.setSizes([740, 860])
    return split


def detail_grid(tr: Text) -> tuple[QGridLayout, dict[str, QLabel]]:
    """Lay out report fields in two vertical groups and return the value labels."""
    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(3)
    values: dict[str, QLabel] = {}
    fields = (
        'vehicle_no',
        'status',
        'battery',
        'connection',
        'stop_reason',
        'vision_reading',
        'dispatch_setting',
        'dispatch_eligibility',
        'observation_received_at',
        'position',
        'reported_yaw',
        'reported_speed',
    )
    for index, key in enumerate(fields):
        column, row = divmod(index, len(fields) // 2)
        name = label(tr(key), 'secondary', wrap=False)
        value = label('—', wrap=False)
        value.setTextFormat(Qt.TextFormat.PlainText)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        grid.addWidget(name, row, 2 * column)
        grid.addWidget(value, row, 2 * column + 1)
        values[key] = value
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(3, 1)
    return grid, values
